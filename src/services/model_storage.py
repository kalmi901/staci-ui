from __future__ import annotations
import re
from pathlib import Path

from src.config import UPLOAD_ROOT

_MODEL_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")

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