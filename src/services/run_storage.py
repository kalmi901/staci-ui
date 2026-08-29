from __future__ import annotations
import re
from pathlib import Path

from src.config import RUN_ROOT

_RUN_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")

def resolve_run_dir(run_id: str) -> Path:
    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(f"Invalid run id: {run_id!r}")

    run_root = RUN_ROOT.resolve()
    run_dir = (run_root / run_id).resolve()

    if not run_dir.is_relative_to(run_root):
        raise ValueError("Invalid run directory.")

    return run_dir