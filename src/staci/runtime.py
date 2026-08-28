from __future__ import annotations

import os
from pathlib import Path

def default_staci_executable() -> Path:
    env_path = os.getenv("STACI_EXECUTABLE")

    if env_path:
        return Path(env_path).expanduser().resolve()

    bin_dir = Path(__file__).resolve().parents[1] / "bin" / "staci"

    executable = "staci.exe" if os.name == "nt" else "staci"

    return bin_dir / executable