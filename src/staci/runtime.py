from __future__ import annotations
from typing import Literal

import os
from pathlib import Path

def default_staci_executable(module: Literal["staci", "staci_split"] = "staci") -> Path:

    bin_dir = Path(__file__).resolve().parents[1] / "bin" / "staci"

    #executable = "staci.exe" if os.name == "nt" else "staci"
    executable = f"{module}.exe" if os.name == "nt" else module

    return bin_dir / executable


def _stream_to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value