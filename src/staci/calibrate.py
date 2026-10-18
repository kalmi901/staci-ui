from __future__ import annotations

import json
import os
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import (
    STACI_CALIBRATE_EXECUTABLE,
    STACI_TIMEOUT_SECONDS,
)
from src.staci.runtime import _stream_to_text


_DEFAULT_SETTINGS: dict[str, Any] = {
    "global_debug_level": 1,
    "Staci_debug_level": 0,
    "fname_prefix": "calibrate_network_",
    "logfilename": "calibrate.log",
    "best_logfilename": "calibrate-best.log",
    "Start_of_Periods": 0,
    "Num_of_Periods": 2,
    "Spoil_Active_Pipes": False,
    "dt": 1.0,
    "weight_p_err": 1.0,
    "type_of_pipe_selection": "largest_diameter",
    "num_of_active_pipes": 1,
    "popsize": 20,
    "ngen": 50,
    "pmut": 0.2,
    "pcross": 0.8,
}

_PIPE_SELECTION_TYPES = {
    "Dmin",
    "most_sensitive",
    "largest_diameter",
}


@dataclass(frozen=True)
class StaciCalibrateResults:
    returncode: int
    stdout_path: Path
    stderr_path: Path
    diagnostics_path: Path
    calibration_log_path: Path
    best_log_path: Path
    best_data_path: Path
    history_path: Path
    sensitivity_mass_flow_path: Path
    sensitivity_pressure_path: Path

    @property
    def success(self) -> bool:
        return (
            self.returncode == 0
            and self.best_data_path.is_file()
            and self.history_path.is_file()
        )


def write_calibrate_settings(
    output_path: Path,
    *,
    measurements_path: Path,
    overrides: dict[str, Any] | None = None,
) -> None:
    output_path = output_path.resolve()
    measurements_path = measurements_path.resolve()
    run_dir = output_path.parent

    if output_path.suffix.lower() != ".json":
        raise ValueError(
            "STACI Calibrate settings must use the .json extension."
        )

    if measurements_path.parent != run_dir:
        raise ValueError(
            "STACI Calibrate measurements must be located "
            "beside the settings file."
        )

    settings = {
        **_DEFAULT_SETTINGS,
        **(overrides or {}),
    }

    # These paths are controlled by the wrapper so that every input and
    # output remains inside the isolated run directory.
    settings["dir_name"] = str(run_dir) + os.sep
    settings["sollwert_dfile"] = measurements_path.name

    pipe_selection = settings.get("type_of_pipe_selection")

    if pipe_selection not in _PIPE_SELECTION_TYPES:
        raise ValueError(
            "Unsupported STACI Calibrate pipe selection type: "
            f"{pipe_selection!r}"
        )

    if pipe_selection == "Dmin":
        if "Dmin" not in settings:
            raise ValueError(
                "Dmin is required when type_of_pipe_selection is 'Dmin'."
            )
        settings.pop("num_of_active_pipes", None)
    else:
        settings.pop("Dmin", None)

    output_path.write_text(
        json.dumps(settings, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_settings(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()

    if suffix == ".json":
        settings = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(settings, dict):
            raise ValueError(
                "STACI Calibrate JSON settings must contain an object."
            )

        return settings

    if suffix == ".xml":
        root = ET.parse(path).getroot()

        if root.tag != "settings":
            raise ValueError(
                "STACI Calibrate XML root element must be 'settings'."
            )

        return {
            element.tag: element.text
            for element in root
        }

    raise ValueError(
        "STACI Calibrate settings must use .json or .xml."
    )


def _resolve_output_path(
    run_dir: Path,
    value: object,
    field: str,
) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"STACI Calibrate setting {field!r} "
            "must be a non-empty string."
        )

    path = Path(value)

    if not path.is_absolute():
        path = run_dir / path

    path = path.resolve()

    if not path.is_relative_to(run_dir):
        raise ValueError(
            f"STACI Calibrate output {field!r} "
            "must remain inside the run directory."
        )

    return path


def run_staci_calibrate(
    settings_path: Path,
    *,
    seed: int = 12345,
) -> StaciCalibrateResults:
    if not STACI_CALIBRATE_EXECUTABLE.is_file():
        raise FileNotFoundError(
            "STACI Calibrate executable not found: "
            f"{STACI_CALIBRATE_EXECUTABLE}"
        )

    settings_path = settings_path.resolve()

    if not settings_path.is_file():
        raise FileNotFoundError(
            "STACI Calibrate settings file not found: "
            f"{settings_path}"
        )

    run_dir = settings_path.parent
    settings = _read_settings(settings_path)

    calibration_log_path = _resolve_output_path(
        run_dir,
        settings.get("logfilename"),
        "logfilename",
    )
    best_log_path = _resolve_output_path(
        run_dir,
        settings.get("best_logfilename"),
        "best_logfilename",
    )

    stdout_path = run_dir / "staci_calibrate.stdout.log"
    stderr_path = run_dir / "staci_calibrate.stderr.log"
    diagnostics_path = run_dir / "staci-diagnostics.jsonl"

    best_data_path = run_dir / "best.dat"
    history_path = run_dir / "bog.dat"
    sensitivity_mass_flow_path = (
        run_dir / "sensitivity_MassFlowRates.dat"
    )
    sensitivity_pressure_path = (
        run_dir / "sensitivity_Pressures.dat"
    )

    command = [
        str(STACI_CALIBRATE_EXECUTABLE),
        "--settings",
        str(settings_path),
        "--seed",
        str(seed),
        "--diagnostics-file",
        str(diagnostics_path),
    ]

    try:
        result = subprocess.run(
            command,
            cwd=run_dir,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=STACI_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(
            _stream_to_text(exc.stdout),
            encoding="utf-8",
        )
        stderr_path.write_text(
            _stream_to_text(exc.stderr),
            encoding="utf-8",
        )
        raise TimeoutError(
            "STACI Calibrate exceeded the "
            f"{STACI_TIMEOUT_SECONDS} s timeout."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "STACI Calibrate execution failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    stdout_path.write_text(
        result.stdout or "",
        encoding="utf-8",
    )
    stderr_path.write_text(
        result.stderr or "",
        encoding="utf-8",
    )

    return StaciCalibrateResults(
        returncode=result.returncode,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        diagnostics_path=diagnostics_path,
        calibration_log_path=calibration_log_path,
        best_log_path=best_log_path,
        best_data_path=best_data_path,
        history_path=history_path,
        sensitivity_mass_flow_path=sensitivity_mass_flow_path,
        sensitivity_pressure_path=sensitivity_pressure_path,
    )