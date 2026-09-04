from __future__ import annotations
import json
import subprocess

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from src.config import (
    STACI_EXECUTABLE,
    STACI_TIMEOUT_SECONDS
    )

from src.staci.runtime import _stream_to_text

@dataclass
class StaciEPSResults:
    returncode: int
    output_prefix: Path
    h5_path: Path
    meta_path: Path
    stdout_path: Path
    stderr_path: Path
    meta: Dict[str, Any]

    
def run_staci_eps(
    inp_path: Path,
    output_prefix: Path
) -> StaciEPSResults:
    
    if not STACI_EXECUTABLE.exists():
        raise FileNotFoundError(
            f"STACI executable not found: {STACI_EXECUTABLE}"
        )
        
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
        str(output_prefix)
    ]
    
    try:
        result = subprocess.run(
            command,
            cwd=output_prefix.parent,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=STACI_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text( _stream_to_text(exc.stdout), encoding="utf-8")
        stderr_path.write_text( _stream_to_text(exc.stderr), encoding="utf-8")
        raise TimeoutError(
            f"STACI EPS exceeded the "
            f"{STACI_TIMEOUT_SECONDS} s timeout."
        ) from exc
    
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")

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
        meta=meta
    )