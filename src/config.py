from __future__ import annotations
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_data_root_env = os.getenv("STACI_UI_DATA_DIR")

DATA_ROOT = (
    Path(_data_root_env).expanduser().resolve() 
    if _data_root_env
    else PROJECT_ROOT / "data"
)

UPLOAD_ROOT = DATA_ROOT / "uploads"
RUN_ROOT    = DATA_ROOT / "runs"