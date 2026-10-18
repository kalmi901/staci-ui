from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.config import STACI_CALIBRATE_EXECUTABLE
from src.staci.calibrate import (
    run_staci_calibrate,
    write_calibrate_settings,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"
NETWORK_FIXTURE = FIXTURE_DIR / "staci_calibrate_network_0.spr"
TARGETS_FIXTURE = FIXTURE_DIR / "staci_calibrate_targets.csv"


def _read_if_present(path: Path) -> str:
    if not path.is_file():
        return "<not created>"

    return path.read_text(encoding="utf-8", errors="replace")


@pytest.mark.integration
@pytest.mark.staci
def test_run_staci_calibrate_runs_real_executable(
    tmp_path: Path,
) -> None:
    executable = STACI_CALIBRATE_EXECUTABLE.resolve()
    if not executable.is_file():
        pytest.skip(
            "Real STACI Calibrate executable is not available. "
            "Set STACI_CALIBRATE_EXECUTABLE to run this test."
        )

    network_path = tmp_path / "calibrate_network_0.spr"
    targets_path = tmp_path / "calibrate_targets.csv"
    settings_path = tmp_path / "staci_calibrate_settings.json"

    shutil.copy2(NETWORK_FIXTURE, network_path)
    shutil.copy2(TARGETS_FIXTURE, targets_path)

    write_calibrate_settings(
        settings_path,
        measurements_path=targets_path,
        overrides={
            "global_debug_level": 0,
            "Num_of_Periods": 1,
            "popsize": 4,
            "ngen": 1,
        },
    )

    result = run_staci_calibrate(settings_path, seed=12345)

    assert result.success, (
        f"STACI Calibrate failed with return code {result.returncode}.\n"
        f"stdout:\n{_read_if_present(result.stdout_path)}\n"
        f"stderr:\n{_read_if_present(result.stderr_path)}\n"
        "diagnostics:\n"
        f"{_read_if_present(result.diagnostics_path)}"
    )

    assert result.returncode == 0
    assert result.best_data_path.is_file()
    assert result.best_data_path.stat().st_size > 0
    assert result.history_path.is_file()
    assert result.history_path.stat().st_size > 0
    assert result.calibration_log_path.is_file()
    assert result.best_log_path.is_file()
    assert result.sensitivity_mass_flow_path.is_file()
    assert result.sensitivity_pressure_path.is_file()

    assert "Optimization finished" in result.stdout_path.read_text(
        encoding="utf-8",
        errors="replace",
    )
