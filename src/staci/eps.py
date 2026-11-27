from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from src.config import STACI_EXECUTABLE, STACI_TIMEOUT_SECONDS
from src.staci.runtime import run_staci_process


@dataclass
class StaciEPSResults:
    returncode: int
    output_prefix: Path
    h5_path: Path
    meta_path: Path
    stdout_path: Path
    stderr_path: Path
    meta: Dict[str, Any]


def run_staci_eps(inp_path: Path, output_prefix: Path) -> StaciEPSResults:

    if not STACI_EXECUTABLE.exists():
        raise FileNotFoundError(f"STACI executable not found: {STACI_EXECUTABLE}")

    inp_path = inp_path.resolve()
    output_prefix = output_prefix.resolve()

    stdout_path = output_prefix.parent / "staci.stdout.log"
    stderr_path = output_prefix.parent / "staci.stderr.log"

    # Run Staci Extended Period Simulation
    # https://github.com/hoscsaba/staci/tree/master#run-an-epanet-extended-period-simulation
    command = [
        str(STACI_EXECUTABLE),
        "--epanet-eps",
        str(inp_path),
        "-o",
        str(output_prefix),
    ]

    result = run_staci_process(
        command,
        cwd=output_prefix.parent,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        timeout_seconds=STACI_TIMEOUT_SECONDS,
        operation="STACI EPS",
    )

    h5_path = output_prefix.with_suffix(".h5")
    meta_path = output_prefix.with_suffix(".meta.json")

    meta: dict[str, Any] = {}

    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    return StaciEPSResults(
        returncode=result.returncode,
        output_prefix=output_prefix,
        h5_path=h5_path,
        meta_path=meta_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        meta=meta,
    )
