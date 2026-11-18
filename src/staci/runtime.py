from __future__ import annotations

from collections.abc import Sequence
import os
from pathlib import Path
import subprocess
from typing import Literal


def default_staci_executable(
    module: Literal[
        "staci",
        "staci_split",
        "staci_calibrate",
        "staci_flush",
    ] = "staci",
) -> Path:
    bin_dir = (
        Path(__file__).resolve().parents[1]
        / "bin"
        / "staci"
    )

    executable = (
        f"{module}.exe"
        if os.name == "nt"
        else module
    )

    return bin_dir / executable


def _stream_to_text(
    value: str | bytes | None,
) -> str:
    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode(
            "utf-8",
            errors="replace",
        )

    return value


def _write_process_logs(
    stdout_path: Path,
    stderr_path: Path,
    *,
    stdout: str | bytes | None,
    stderr: str | bytes | None,
) -> None:
    stdout_path.write_text(
        _stream_to_text(stdout),
        encoding="utf-8",
    )
    stderr_path.write_text(
        _stream_to_text(stderr),
        encoding="utf-8",
    )


def run_staci_process(
    command: Sequence[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: int | float,
    operation: str,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        _write_process_logs(
            stdout_path,
            stderr_path,
            stdout=exc.stdout,
            stderr=exc.stderr,
        )
        raise TimeoutError(
            f"{operation} exceeded the "
            f"{timeout_seconds} s timeout."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"{operation} execution failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    _write_process_logs(
        stdout_path,
        stderr_path,
        stdout=result.stdout,
        stderr=result.stderr,
    )

    return result