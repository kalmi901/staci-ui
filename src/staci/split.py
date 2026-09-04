from __future__ import annotations
import subprocess
import xml.etree.ElementTree as ET

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Literal

from src.config import (
    STACI_SPLIT_EXECUTABLE,
    STACI_TIMEOUT_SECONDS
)

from src.staci.runtime import _stream_to_text

@dataclass
class SplitConfig:
    fname: str
    # Defaults
    global_debug_level: int = 1
    n_comm: int = 3
    weight_type: Literal["topology", "dp","sensitivity"] = "topology"
    weight_type_mod: Literal["friction_coeff", "demand", "diameter"] = "diameter"
    logfilename: str = "split.log"
    obj_type: Literal["modularity", "A-optimality", "D-optimality"] = "modularity"
    # GA-parameters
    popsize: int = 20
    ngen: int = 50
    pmut: float = 0.25
    pcross: float = 0.8


@dataclass
class StaciSplitResults:
    returncode: int | None
    stdout_path: Path
    stderr_path: Path
    timed_out: bool = False
    membership_path: Path | None = None
    
    @property
    def success(self) -> bool:
        return (
            not self.timed_out
            and self.returncode == 0
            and self.membership_path is not None
        )
    
    
def write_split_settings(
    output_path: Path,
    *,
    inp_path: Path,
    overrides: Dict[str, Any] | None = None
    ) -> None:

    config_data = {
        **(overrides or {}),
        "fname": str(inp_path.resolve()),
    }

    split_config = SplitConfig(**config_data)
    
    root = ET.Element("settings")
    
    for key, value in asdict(split_config).items():
        element = ET.SubElement(root, key)
        element.text = str(value)
        
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    
    tree.write(
        output_path,
        encoding="utf-8",
        xml_declaration=True,
    )
    
def run_staci_split(
    inp_path: Path,
    staci_split_settings_xml: Path,
    seed: int = 1
) -> StaciSplitResults:
    if not STACI_SPLIT_EXECUTABLE.exists():
        raise FileNotFoundError(
            f"STACI_SPLIT executable not found: {STACI_SPLIT_EXECUTABLE}"
        )
     
    run_dir = inp_path.resolve().parent
    expected_settings = run_dir / "staci_split_settings.xml"
    
    if staci_split_settings_xml.resolve() != expected_settings.resolve():
        raise ValueError(
            f"Invalid STACI Split settings path: "
            f"{staci_split_settings_xml}. "
            f"Expected: {expected_settings}"
        )

    if not expected_settings.is_file():
        raise FileNotFoundError(
            f"STACI Split settings file not found: {expected_settings}"
        )
    
    
    stdout_path = run_dir / "staci_split.stdout.log"
    stderr_path = run_dir / "staci_split.stderr.log"
    membership_path = run_dir / "membership.txt"
    
    command = [
        str(STACI_SPLIT_EXECUTABLE),
        "--seed",
        str(seed),
    ]
    
    try:
        result = subprocess.run(
            command,
            cwd=run_dir,
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
            f"STACI Split exceeded the "
            f"{STACI_TIMEOUT_SECONDS} s timeout."
        ) from exc
        
    except Exception as exc:
        raise RuntimeError(
            f"STACI Split execution failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    stdout_path.write_text(result.stdout or "", encoding="utf-8")
    stderr_path.write_text(result.stderr or "", encoding="utf-8")
    
    return StaciSplitResults(
        returncode=result.returncode,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        timed_out=False,
        membership_path=(
            membership_path
            if membership_path.is_file()
            else None
        ),
    )
