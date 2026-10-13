"""Correlate existing request logs without changing solver inputs or results."""
from contextvars import ContextVar
from functools import lru_cache, wraps
import hashlib
from importlib.metadata import version
import inspect
import json
import logging
from pathlib import Path
import platform
import time
import uuid


execution_id = ContextVar("staci_execution_id", default="-")
logger = logging.getLogger(__name__)


def file_sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@lru_cache(maxsize=1)
def application_version():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    files = [root / "app.py", *sorted((root / "src").rglob("*.py")),
             *sorted(root.glob("requirements*.txt"))]
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {"source_sha256": digest.hexdigest(), "python": platform.python_version(),
            "wntr": version("wntr")}


@lru_cache(maxsize=8)
def _binary_sha256(path, size, modified):
    return file_sha256(path)


def event(kind, **values):
    # Logging metadata must never turn a valid calculation into a failed one.
    try:
        logger.info("STACI_RUN %s", json.dumps(
            {"schema": 1, "event": kind, "execution_id": execution_id.get(), **values},
            ensure_ascii=True, allow_nan=False, separators=(",", ":")))
    except Exception:
        logger.warning("Run metadata could not be recorded", exc_info=True)


def log_prepared_input(inp_path, run_id, *, options_reader=None, settings_path=None,
                       executable=None):
    if execution_id.get() == "-":
        return
    # Record the allocated result directory even if metadata inspection fails.
    event("allocated", run_id=run_id)
    try:
        data = {"run_id": run_id, "input_sha256": file_sha256(inp_path)}
        if options_reader:
            data["effective_options"] = options_reader(inp_path)
        if settings_path:
            settings_key = "settings_json" if Path(settings_path).suffix == ".json" else "settings_xml"
            data[settings_key] = Path(settings_path).read_text(encoding="utf-8")
        if executable:
            path = Path(executable)
            stat = path.stat()
            data["solver_sha256"] = _binary_sha256(str(path), stat.st_size, stat.st_mtime_ns)
        event("prepared", **data)
    except Exception:
        logger.warning("Run input metadata incomplete", exc_info=True)


def logged_run(run_type):
    """Wrap a Dash run callback; preserve its return value and exception behavior."""
    def decorate(function):
        signature = inspect.signature(function)

        @wraps(function)
        def wrapped(*args, **kwargs):
            values = signature.bind(*args, **kwargs).arguments
            model = values.get("network_state")
            if not values.get("n_clicks") or not model:
                return function(*args, **kwargs)
            token = execution_id.set(uuid.uuid4().hex)
            started = time.monotonic()
            try:
                event("started", run_type=run_type, model_id=model.get("model_id", ""),
                      filename=model.get("filename", ""),
                      settings={key: value for key, value in values.items()
                                if key not in ("n_clicks", "network_state")})
                try:
                    from src.config import STACI_TIMEOUT_SECONDS
                    event("environment", versions=application_version(),
                          timeout_seconds=STACI_TIMEOUT_SECONDS)
                except Exception:
                    logger.warning("Run version metadata incomplete", exc_info=True)
                try:
                    result = function(*args, **kwargs)
                except Exception as error:
                    event("finished", status="failed", error=str(error),
                          elapsed_seconds=round(time.monotonic() - started, 3))
                    logger.exception("Run callback raised an exception")
                    raise
                state = result[0] if isinstance(result, (tuple, list)) and result else None
                status = "failed" if not isinstance(state, dict) else "completed"
                summary = state.get("summary", {}) if isinstance(state, dict) else {}
                warnings = state.get("staci", {}).get("warnings", []) if isinstance(state, dict) else []
                if status == "completed" and (summary.get("failed_frames", 0) or warnings or state.get("partial")):
                    status = "completed_with_warnings"
                event("finished", status=status,
                      run_id=state.get("run_id", "") if isinstance(state, dict) else "",
                      summary=summary, warnings=warnings,
                      elapsed_seconds=round(time.monotonic() - started, 3))
                return result
            finally:
                execution_id.reset(token)
        return wrapped
    return decorate
