from __future__ import annotations

import sys
from pathlib import Path

import pytest

from src.services.solver_jobs import (
    SolverJobCancelledError,
    solver_cancellation_scope,
)
from src.staci.runtime import run_staci_process


def test_run_staci_process_stops_cancelled_process(
    tmp_path: Path,
) -> None:
    with (
        solver_cancellation_scope(lambda: True),
        pytest.raises(
            SolverJobCancelledError,
            match="was cancelled",
        ),
    ):
        run_staci_process(
            [
                sys.executable,
                "-c",
                "import time; time.sleep(30)",
            ],
            cwd=tmp_path,
            stdout_path=tmp_path / "stdout.log",
            stderr_path=tmp_path / "stderr.log",
            timeout_seconds=60,
            operation="Test process",
        )
