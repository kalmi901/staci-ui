from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from src.config import STACI_FLUSH_EXECUTABLE
from src.staci.flush import run_staci_flush


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "staci_flush_network.inp"
)


@pytest.mark.integration
@pytest.mark.staci
def test_run_staci_flush_runs_real_executable(tmp_path: Path) -> None:
    executable = STACI_FLUSH_EXECUTABLE.resolve()
    if not executable.is_file():
        pytest.skip(
            "Real STACI Flush executable is not available. "
            "Set STACI_FLUSH_EXECUTABLE to run this test."
        )

    inp_path = tmp_path / "network.inp"
    shutil.copy2(FIXTURE_PATH, inp_path)

    output_dir = tmp_path / "flushing-output"
    config_path = tmp_path / "flushing_config.json"

    config_path.write_text(
        json.dumps(
            {
                "mode": "single",
                "hydrant_node_ids": ["A", "B", "C"],
                "hydrant_area_m2": 0.002,
                "total_loss_coefficient": 2.0,
                "velocity_threshold_mps": 0.5,
                "min_pressure_head_m": 0.0,
                "output_dir": output_dir.name,
                "write_network_files": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_staci_flush(inp_path, config_path)

    assert result.success, (
        f"STACI Flush failed with return code {result.returncode}.\n"
        f"stdout:\n"
        f"{result.stdout_path.read_text(encoding='utf-8', errors='replace')}\n"
        f"stderr:\n"
        f"{result.stderr_path.read_text(encoding='utf-8', errors='replace')}"
    )

    assert result.returncode == 0
    assert result.output_dir == output_dir.resolve()

    assert result.run_json_path.is_file()
    assert result.scenarios_path.is_file()
    assert result.plan_csv_path.is_file()
    assert result.plan_text_path.is_file()
    assert result.pipe_travel_times_path.is_file()
    assert result.pipes_above_threshold_path.is_file()
    assert result.pipe_coverage_path.is_file()

    with result.plan_csv_path.open(
        encoding="utf-8",
        newline="",
    ) as plan_file:
        plan_rows = list(csv.DictReader(plan_file))

    assert [row["node_id"] for row in plan_rows] == ["C", "B", "A"]
    assert float(plan_rows[-1]["cumulative_volume_percent"]) == pytest.approx(
        100.0
    )