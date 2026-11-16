from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.config import STACI_CALIBRATE_EXECUTABLE
from src.staci.calibrate import (
    run_staci_calibrate,
    write_calibrate_settings,
)

from src.results.calibration import (
    parse_calibration_best,
    parse_calibration_history
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"
NETWORK_FIXTURES = (
    FIXTURE_DIR / "staci_calibrate_network_0.inp",
    FIXTURE_DIR / "staci_calibrate_network_1.inp",
)
MEASUREMENTS_FIXTURE = (
    FIXTURE_DIR / "staci_calibrate_measurements.json"
)


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


    targets_path = tmp_path / "calibrate_targets.json"
    settings_path = tmp_path / "staci_calibrate_settings.json"

    for index, fixture_path in enumerate(NETWORK_FIXTURES):
        shutil.copy2(
            fixture_path,
            tmp_path / f"network_{index}.inp",
        )
    measurements_path = tmp_path / "measurements.json"
    shutil.copy2(MEASUREMENTS_FIXTURE, measurements_path)

    write_calibrate_settings(
        settings_path,
        measurements_path=measurements_path,
        snapshot_count=2,
        overrides={
            "global_debug_level": 0,
            "dt": 0.01,
            "weight_p_err": 0.5,
            "type_of_pipe_selection": "list",
            "pipe_ids": ["Large"],
            "min_diameter_m": 0.15,
            "max_diameter_m": 0.25,
            "popsize": 6,
            "ngen": 10,
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

    best = parse_calibration_best(result.best_data_path)
    history = parse_calibration_history(result.history_path)

    assert [pipe.pipe_id for pipe in best.pipes] == ["Large"]
    assert 0.15 <= best.pipes[0].diameter_m <= 0.25
    assert len(best.comparisons) == 4

    assert history
    assert all(
        entry.function_evaluations >= 0
        for entry in history
    )
