from __future__ import annotations
import os
from pathlib import Path

from src.staci.runtime import default_staci_executable

APP_URL_PREFIX = os.getenv("STACI_UI_URL_PREFIX", "/staci-app/")
if (
    not APP_URL_PREFIX.startswith("/")
    or not APP_URL_PREFIX.endswith("/")
    or "//" in APP_URL_PREFIX
    or any(character in APP_URL_PREFIX for character in "?#\\")
    or any(segment in (".", "..") for segment in APP_URL_PREFIX.split("/"))
):
    raise ValueError("STACI_UI_URL_PREFIX must be an absolute URL path ending in '/'.")


DASH_DEBUG = os.getenv("DASH_DEBUG", "0") == "1"

CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://localhost:6379/0",
)

CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://localhost:6379/1",
)

CELERY_RESULT_EXPIRES_SECONDS = int(
    os.getenv("CELERY_RESULT_EXPIRES_SECONDS", "3600")
)

if CELERY_RESULT_EXPIRES_SECONDS <= 0:
    raise ValueError(
        "CELERY_RESULT_EXPIRES_SECONDS must be positive."
    )

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
_staci_flush_executable = os.getenv("STACI_FLUSH_EXECUTABLE")

STACI_EXECUTABLE = (
    Path(_staci_executable).expanduser().resolve() 
    if _staci_executable
    else default_staci_executable("staci"))

STACI_SPLIT_EXECUTABLE = (
    Path(_staci_split_executable).expanduser().resolve()
    if _staci_split_executable
    else default_staci_executable("staci_split"))

STACI_FLUSH_EXECUTABLE = (
    Path(_staci_flush_executable).expanduser().resolve()
    if _staci_flush_executable
    else default_staci_executable("staci_flush")
)

STACI_TIMEOUT_SECONDS = int(
    os.getenv("STACI_TIMEOUT_SECONDS", "300")
)
