from __future__ import annotations
import os
from pathlib import Path

from src.staci.runtime import default_staci_executable

APP_ENV = os.getenv("STACI_UI_ENV", "development").lower()

DASH_USER = os.getenv("DASH_USER", "staci")
DASH_PASSWORD = os.getenv("DASH_PASSWORD", "staci")
DASH_AUTH_SECRET = os.getenv("DASH_AUTH_SECRET", "manbearpig")

if APP_ENV == "production":
    required = {
        "DASH_USER": os.getenv("DASH_USER"),
        "DASH_PASSWORD": os.getenv("DASH_PASSWORD"),
        "DASH_AUTH_SECRET": os.getenv("DASH_AUTH_SECRET"),
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing required production environment variables: "
            + ", ".join(missing)
        )


DASH_DEBUG = os.getenv("DASH_DEBUG", "0") == "1"
PORT = int(os.getenv("PORT", "8050"))

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_data_root_env = os.getenv("STACI_UI_DATA_DIR")

DATA_ROOT = (
    Path(_data_root_env).expanduser().resolve() 
    if _data_root_env
    else PROJECT_ROOT / "data"
)

UPLOAD_ROOT = DATA_ROOT / "uploads"
RUN_ROOT    = DATA_ROOT / "runs"

_staci_executable = os.getenv("STACI_EXECUTABLE")
_staci_split_executable = os.getenv("STACI_SPLIT_EXECUTABLE")

STACI_EXECUTABLE = (
    Path(_staci_executable).expanduser().resolve() 
    if _staci_executable
    else default_staci_executable("staci"))

STACI_SPLIT_EXECUTABLE = (
    Path(_staci_split_executable).expanduser().resolve()
    if _staci_split_executable
    else default_staci_executable("staci_split"))

STACI_TIMEOUT_SECONDS = int(
    os.getenv("STACI_TIMEOUT_SECONDS", "300")
)