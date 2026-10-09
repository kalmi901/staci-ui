from __future__ import annotations

import argparse
import re
import json
import math
import shutil
import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode


def _http_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_seconds: float,
) -> tuple[dict[str, Any], bytes]:
    data = None
    headers: dict[str, str] = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    started = time.perf_counter()
    body = b""
    status: int | None = None
    error: str | None = None

    try:
        with urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            body = response.read()
            status = response.status

    except HTTPError as exc:
        body = exc.read()
        status = exc.code
        error = str(exc)

    except (URLError, TimeoutError, OSError) as exc:
        error = str(exc)

    latency_seconds = time.perf_counter() - started

    metric = {
        "status": status,
        "latency_ms": round(latency_seconds * 1000.0, 3),
        "response_bytes": len(body),
        "error": error,
    }

    return metric, body


def _load_dash_end_id(
    index_url: str,
    *,
    timeout_seconds: float,
) -> str:
    metric, body = _http_request(
        index_url,
        timeout_seconds=timeout_seconds,
    )

    if metric["status"] != 200:
        raise RuntimeError(
            "Could not load the Dash index page: "
            f"{metric}"
        )

    match = re.search(
        rb"<script[^>]*\bid=['\"]_dash-config['\"][^>]*>"
        rb"(.*?)</script>",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if match is None:
        raise RuntimeError(
            "Dash index page did not contain _dash-config"
        )

    config = json.loads(match.group(1))
    end_id = config.get("end_id")

    if not isinstance(end_id, str) or not end_id:
        raise RuntimeError(
            "Dash configuration did not contain end_id"
        )

    return end_id


def _find_hydraulic_callback_output(
    dependencies_url: str,
    *,
    timeout_seconds: float,
) -> str:
    metric, body = _http_request(
        dependencies_url,
        timeout_seconds=timeout_seconds,
    )

    if metric["status"] != 200:
        raise RuntimeError(
            "Could not load Dash callback dependencies: "
            f"{metric}"
        )

    dependencies = json.loads(body)

    matches = [
        dependency["output"]
        for dependency in dependencies
        if (
            "hyd-run-store.data" in dependency["output"]
            and "hyd-run-status.children"
            in dependency["output"]
        )
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one hydraulic run callback, "
            f"found {len(matches)}: {matches}"
        )

    return matches[0]


def _prepare_models(
    data_root: Path,
    model_path: Path,
    job_count: int,
) -> list[dict[str, str]]:
    uploads_root = data_root / "uploads"
    uploads_root.mkdir(parents=True, exist_ok=True)

    models: list[dict[str, str]] = []

    for index in range(job_count):
        model_id = uuid.uuid4().hex[:12]
        filename = "benchmark.inp"

        model_dir = uploads_root / model_id
        model_dir.mkdir(parents=True, exist_ok=False)

        shutil.copy2(
            model_path,
            model_dir / filename,
        )

        models.append(
            {
                "model_id": model_id,
                "filename": filename,
            }
        )

    return models


def _make_hydraulic_payload(
    callback_output: str,
    network_state: dict[str, str],
    *,
    duration_hours: float,
    timestep_minutes: float,
) -> dict[str, Any]:
    return {
        "output": callback_output,
        "outputs": [
            {
                "id": "hyd-run-store",
                "property": "data",
            },
            {
                "id": "hyd-run-status",
                "property": "children",
            },
        ],
        "inputs": [
            {
                "id": "hyd-run-button",
                "property": "n_clicks",
                "value": 1,
            }
        ],
        "state": [
            {
                "id": "network-store",
                "property": "data",
                "value": network_state,
            },
            {
                "id": "hyd-backend",
                "property": "value",
                "value": "staci",
            },
            {
                "id": "hyd-override-options",
                "property": "value",
                "value": True,
            },
            {
                "id": "hyd-duration-hours",
                "property": "value",
                "value": duration_hours,
            },
            {
                "id": "hyd-timestep-minutes",
                "property": "value",
                "value": timestep_minutes,
            },
        ],
        "changedPropIds": [
            "hyd-run-button.n_clicks"
        ],
    }


def _run_callback(
    update_url: str,
    end_id: str,
    callback_output: str,
    network_state: dict[str, str],
    start_event: threading.Event,
    *,
    duration_hours: float,
    timestep_minutes: float,
    poll_interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    payload = _make_hydraulic_payload(
        callback_output,
        network_state,
        duration_hours=duration_hours,
        timestep_minutes=timestep_minutes,
    )

    start_event.wait()
    started = time.perf_counter()
    deadline = started + timeout_seconds

    initial_url = (
        f"{update_url}?"
        + urlencode({"endId": end_id})
    )

    metric, body = _http_request(
        initial_url,
        method="POST",
        payload=payload,
        timeout_seconds=timeout_seconds,
    )

    metric["model_id"] = network_state["model_id"]
    metric["enqueue_latency_ms"] = metric["latency_ms"]
    metric["poll_count"] = 0

    if metric["status"] != 200:
        metric["response_preview"] = body[
            :1000
        ].decode("utf-8", errors="replace")
        return metric

    enqueue_latency_ms = metric["enqueue_latency_ms"]
    initial_response = json.loads(body)

    cache_key = initial_response.get("cacheKey")
    job = initial_response.get("job")

    if not isinstance(cache_key, str) or not isinstance(
        job,
        str,
    ):
        raise RuntimeError(
            "Background callback start response did not "
            "contain cacheKey and job handles: "
            f"{initial_response}"
        )

    # The Dash renderer also clears input/state values during
    # polling because the background task already owns them.
    poll_payload = {
        **payload,
        "inputs": [
            {**item, "value": None}
            for item in payload["inputs"]
        ],
        "state": [
            {**item, "value": None}
            for item in payload["state"]
        ],
    }

    poll_url = (
        f"{update_url}?"
        + urlencode(
            {
                "endId": end_id,
                "cacheKey": cache_key,
                "job": job,
            }
        )
    )

    poll_count = 0

    while True:
        remaining_seconds = deadline - time.perf_counter()

        if remaining_seconds <= 0:
            return {
                "model_id": network_state["model_id"],
                "status": None,
                "latency_ms": round(
                    (time.perf_counter() - started)
                    * 1000.0,
                    3,
                ),
                "enqueue_latency_ms": enqueue_latency_ms,
                "poll_count": poll_count,
                "response_bytes": 0,
                "error": (
                    "Background callback did not finish "
                    f"within {timeout_seconds} seconds"
                ),
            }

        time.sleep(
            min(
                poll_interval_seconds,
                remaining_seconds,
            )
        )

        remaining_seconds = deadline - time.perf_counter()

        if remaining_seconds <= 0:
            continue

        metric, body = _http_request(
            poll_url,
            method="POST",
            payload=poll_payload,
            timeout_seconds=remaining_seconds,
        )

        poll_count += 1
        last_request_latency_ms = metric["latency_ms"]

        metric.update(
            {
                "model_id": network_state["model_id"],
                "latency_ms": round(
                    (time.perf_counter() - started)
                    * 1000.0,
                    3,
                ),
                "enqueue_latency_ms": enqueue_latency_ms,
                "poll_count": poll_count,
                "last_request_latency_ms": (
                    last_request_latency_ms
                ),
            }
        )

        if metric["status"] != 200:
            metric["response_preview"] = body[
                :1000
            ].decode("utf-8", errors="replace")
            return metric

        poll_response = json.loads(body)

        if "response" in poll_response:
            return metric


def _run_probe(
    layout_url: str,
    start_event: threading.Event,
    delay_seconds: float,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    start_event.wait()
    time.sleep(delay_seconds)

    metric, body = _http_request(
        layout_url,
        timeout_seconds=timeout_seconds,
    )

    metric["scheduled_delay_ms"] = round(
        delay_seconds * 1000.0,
        3,
    )

    if metric["status"] != 200:
        metric["response_preview"] = body[
            :500
        ].decode("utf-8", errors="replace")

    return metric


def _percentile(
    values: list[float],
    percentile: float,
) -> float | None:
    if not values:
        return None

    ordered = sorted(values)
    index = max(
        0,
        math.ceil(percentile * len(ordered)) - 1,
    )
    return ordered[index]


def _summarize(
    metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    successful = [
        metric["latency_ms"]
        for metric in metrics
        if metric["status"] == 200
    ]

    failed = [
        metric
        for metric in metrics
        if metric["status"] != 200
    ]

    if not successful:
        return {
            "count": len(metrics),
            "successful": 0,
            "failed": len(failed),
            "min_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "max_ms": None,
        }

    return {
        "count": len(metrics),
        "successful": len(successful),
        "failed": len(failed),
        "min_ms": round(min(successful), 3),
        "p50_ms": round(
            statistics.median(successful),
            3,
        ),
        "p95_ms": round(
            _percentile(successful, 0.95) or 0.0,
            3,
        ),
        "max_ms": round(max(successful), 3),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure Dash HTTP responsiveness while real "
            "STACI hydraulic callbacks are running."
        )
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8050/staci-app",
    )
    parser.add_argument(
        "--model",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=4,
    )
    parser.add_argument(
        "--duration-hours",
        type=float,
        default=720.0,
    )
    parser.add_argument(
        "--timestep-minutes",
        type=float,
        default=60.0,
    )
    parser.add_argument(
        "--idle-probes",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--loaded-probes",
        type=int,
        default=12,
    )
    parser.add_argument(
        "--probe-start-delay-seconds",
        type=float,
        default=0.25,
    )
    parser.add_argument(
        "--probe-interval-seconds",
        type=float,
        default=0.25,
    )
    parser.add_argument(
        "--callback-poll-interval-seconds",
        type=float,
        default=0.5,
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=660.0,
    )

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.jobs <= 0:
        raise ValueError("--jobs must be positive")

    if args.callback_poll_interval_seconds <= 0:
        raise ValueError(
            "--callback-poll-interval-seconds must be "
            "positive"
        )

    model_path = args.model.expanduser().resolve()
    data_root = args.data_root.expanduser().resolve()

    if not model_path.is_file():
        raise FileNotFoundError(
            f"Benchmark model does not exist: {model_path}"
        )

    data_root.mkdir(parents=True, exist_ok=True)

    base_url = args.base_url.rstrip("/")
    index_url = f"{base_url}/"
    dependencies_url = (
        f"{base_url}/_dash-dependencies"
    )
    layout_url = f"{base_url}/_dash-layout"
    update_url = (
        f"{base_url}/_dash-update-component"
    )

    end_id = _load_dash_end_id(
        index_url,
        timeout_seconds=(
            args.request_timeout_seconds
        ),
    )

    callback_output = (
        _find_hydraulic_callback_output(
            dependencies_url,
            timeout_seconds=(
                args.request_timeout_seconds
            ),
        )
    )

    network_states = _prepare_models(
        data_root,
        model_path,
        args.jobs,
    )

    idle_metrics: list[dict[str, Any]] = []

    for _ in range(args.idle_probes):
        metric, _ = _http_request(
            layout_url,
            timeout_seconds=(
                args.request_timeout_seconds
            ),
        )
        idle_metrics.append(metric)

    start_event = threading.Event()

    worker_count = (
        args.jobs + args.loaded_probes
    )

    with ThreadPoolExecutor(
        max_workers=worker_count
    ) as executor:
        callback_futures = [
            executor.submit(
                _run_callback,
                update_url,
                end_id,
                callback_output,
                network_state,
                start_event,
                duration_hours=(
                    args.duration_hours
                ),
                timestep_minutes=(
                    args.timestep_minutes
                ),
                poll_interval_seconds=(
                    args.callback_poll_interval_seconds
                ),
                timeout_seconds=(
                    args.request_timeout_seconds
                ),
            )
            for network_state in network_states
        ]

        probe_futures = [
            executor.submit(
                _run_probe,
                layout_url,
                start_event,
                (
                    args.probe_start_delay_seconds
                    + index
                    * args.probe_interval_seconds
                ),
                timeout_seconds=(
                    args.request_timeout_seconds
                ),
            )
            for index in range(
                args.loaded_probes
            )
        ]

        benchmark_started = time.perf_counter()
        start_event.set()

        callback_metrics = [
            future.result()
            for future in callback_futures
        ]

        loaded_metrics = [
            future.result()
            for future in probe_futures
        ]

        benchmark_seconds = (
            time.perf_counter()
            - benchmark_started
        )

    idle_summary = _summarize(idle_metrics)
    loaded_summary = _summarize(
        loaded_metrics
    )
    callback_summary = _summarize(
        callback_metrics
    )

    degradation_ratio = None

    if (
        idle_summary["p95_ms"]
        and loaded_summary["p95_ms"]
    ):
        degradation_ratio = round(
            loaded_summary["p95_ms"]
            / idle_summary["p95_ms"],
            2,
        )

    report = {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "configuration": {
            "base_url": base_url,
            "model": str(model_path),
            "data_root": str(data_root),
            "jobs": args.jobs,
            "duration_hours": (
                args.duration_hours
            ),
            "timestep_minutes": (
                args.timestep_minutes
            ),
            "requested_steps": int(
                args.duration_hours
                * 60.0
                / args.timestep_minutes
            ),
            "loaded_probes": (
                args.loaded_probes
            ),
            "callback_poll_interval_seconds": (
                args.callback_poll_interval_seconds
            )
        },
        "benchmark_seconds": round(
            benchmark_seconds,
            3,
        ),
        "idle_http_summary": idle_summary,
        "loaded_http_summary": (
            loaded_summary
        ),
        "callback_summary": callback_summary,
        "loaded_to_idle_p95_ratio": (
            degradation_ratio
        ),
        "idle_http_requests": idle_metrics,
        "loaded_http_requests": loaded_metrics,
        "callback_requests": callback_metrics,
    }

    rendered = json.dumps(
        report,
        indent=2,
        sort_keys=True,
    )

    print(rendered)

    if args.output:
        output_path = (
            args.output.expanduser().resolve()
        )
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output_path.write_text(
            rendered + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()