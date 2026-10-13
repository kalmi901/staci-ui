from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import TypedDict

from src.config import UPLOAD_ROOT


_MODEL_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")
_UNSAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


class StoredModel(TypedDict):
    model_id: str
    filename: str
    path: str
    size_bytes: int


def _safe_filename(filename: str) -> str:
    name = Path((filename or "network.inp").replace("\\", "/")).name
    name = _UNSAFE_FILENAME_PATTERN.sub("_", name)
    return name or "network.inp"


def store_uploaded_model(
    filename: str,
    file_bytes: bytes,
) -> StoredModel:
    model_id = uuid.uuid4().hex[:12]
    safe_name = _safe_filename(filename)

    model_dir = Path(UPLOAD_ROOT) / model_id
    model_dir.mkdir(parents=True, exist_ok=False)

    stored_path = model_dir / safe_name
    stored_path.write_bytes(file_bytes)

    return {
        "model_id": model_id,
        "filename": safe_name,
        "path": str(stored_path),
        "size_bytes": len(file_bytes),
    }


def resolve_uploaded_model(
    model_id: str,
    filename: str,
) -> Path:
    if not _MODEL_ID_PATTERN.fullmatch(model_id):
        raise ValueError(f"Invalid model id: {model_id!r}")

    upload_root = UPLOAD_ROOT.resolve()

    path = (
        upload_root
        / model_id
        / Path(filename).name
    ).resolve()

    if not path.is_relative_to(upload_root):
        raise ValueError("Invalid uploaded model path.")

    if not path.is_file():
        raise FileNotFoundError(
            f"Uploaded model does not exist: {path}"
        )

    return path