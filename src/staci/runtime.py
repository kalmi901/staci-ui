from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from src.services.solver_jobs import (
    SolverJobCancelledError,
    solver_cancellation_enabled,
    solver_cancellation_requested,
)


def default_staci_executable(
    module: Literal[
        "staci",
        "staci_split",
        "staci_calibrate",
        "staci_flush",
    ] = "staci",
) -> Path:
    bin_dir = Path(__file__).resolve().parents[1] / "bin" / "staci"

    executable = f"{module}.exe" if os.name == "nt" else module

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


def _stop_process(
    process: subprocess.Popen[str],
) -> tuple[str, str]:
    if process.poll() is None:
        process.terminate()

    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        return process.communicate()


def _run_cancellable_process(
    command: Sequence[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: int | float,
    operation: str,
) -> subprocess.CompletedProcess[str]:
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
        )
    except OSError as exc:
        raise RuntimeError(
            f"{operation} execution failed: {type(exc).__name__}: {exc}"
        ) from exc

    deadline = time.monotonic() + float(timeout_seconds)

    while True:
        remaining = deadline - time.monotonic()

        if remaining <= 0:
            stdout, stderr = _stop_process(process)

            _write_process_logs(
                stdout_path,
                stderr_path,
                stdout=stdout,
                stderr=stderr,
            )

            raise TimeoutError(f"{operation} exceeded the {timeout_seconds} s timeout.")

        try:
            stdout, stderr = process.communicate(timeout=min(0.25, remaining))
            break

        except subprocess.TimeoutExpired:
            if solver_cancellation_requested():
                stdout, stderr = _stop_process(process)

                _write_process_logs(
                    stdout_path,
                    stderr_path,
                    stdout=stdout,
                    stderr=stderr,
                )

                raise SolverJobCancelledError(f"{operation} was cancelled.") from None

    _write_process_logs(
        stdout_path,
        stderr_path,
        stdout=stdout,
        stderr=stderr,
    )

    return subprocess.CompletedProcess(
        args=list(command),
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
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
    if solver_cancellation_enabled():
        return _run_cancellable_process(
            command,
            cwd=cwd,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout_seconds=timeout_seconds,
            operation=operation,
        )
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
            f"{operation} exceeded the {timeout_seconds} s timeout."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"{operation} execution failed: {type(exc).__name__}: {exc}"
        ) from exc

    _write_process_logs(
        stdout_path,
        stderr_path,
        stdout=result.stdout,
        stderr=result.stderr,
    )

    return result
