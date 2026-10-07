import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services import flushing_runner, run_storage
from src.staci.flush import StaciFlushResults


RUN_ID = "123456abcdef"
MODEL_ID = "012345abcdef"


@pytest.fixture
def input_path(tmp_path: Path) -> Path:
    path = tmp_path / "uploaded.inp"
    path.write_text(
        "[TITLE]\nFlush service test\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def run_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    root = tmp_path / "runs"

    monkeypatch.setattr(flushing_runner, "RUN_ROOT", root)
    monkeypatch.setattr(run_storage, "RUN_ROOT", root)
    monkeypatch.setattr(
        flushing_runner.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=f"{RUN_ID}ffff"),
    )

    return root


def _flush_result(
    run_dir: Path,
    returncode: int,
) -> StaciFlushResults:
    output_dir = run_dir / "results"

    return StaciFlushResults(
        returncode=returncode,
        output_dir=output_dir,
        stdout_path=run_dir / "staci_flush.stdout.log",
        stderr_path=run_dir / "staci_flush.stderr.log",
        run_json_path=output_dir / "run.json",
        scenarios_path=output_dir / "scenarios.csv",
        plan_csv_path=output_dir / "flushing_plan.csv",
        plan_text_path=output_dir / "flushing_plan.txt",
        pipe_travel_times_path=(
            output_dir / "pipe_travel_times.csv"
        ),
        pipes_above_threshold_path=(
            output_dir / "pipes_above_threshold.csv"
        ),
        pipe_coverage_path=output_dir / "pipe_coverage.csv",
        scenario_hydrants_path=(
            output_dir / "scenario_hydrants.csv"
        ),
        scenario_pipes_path=(
            output_dir / "scenario_pipes.csv"
        ),
    )


def test_call_staci_flush_service_creates_run_and_returns_results(
    input_path: Path,
    run_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = run_root / "flushing" / RUN_ID

    def fake_run_staci_flush(
        inp_path: Path,
        config_path: Path,
    ) -> StaciFlushResults:
        assert inp_path == run_dir / "model.inp"
        assert config_path == run_dir / "flushing_config.json"

        output_dir = run_dir / "results"
        output_dir.mkdir()

        (output_dir / "run.json").write_text(
            json.dumps({"scenario_count": 2}),
            encoding="utf-8",
        )
        (output_dir / "scenarios.csv").write_text(
            "node_id,status\n"
            "J1,valid\n"
            "J2,valid\n",
            encoding="utf-8",
        )
        (output_dir / "flushing_plan.csv").write_text(
            "rank,node_id,cumulative_volume_percent\n"
            "1,J2,75.0\n"
            "2,J1,100.0\n",
            encoding="utf-8",
        )
        (output_dir / "flushing_plan.txt").touch()
        (run_dir / "staci_flush.stdout.log").touch()
        (run_dir / "staci_flush.stderr.log").touch()

        return _flush_result(run_dir, returncode=0)

    monkeypatch.setattr(
        flushing_runner,
        "run_staci_flush",
        fake_run_staci_flush,
    )

    result = flushing_runner.call_staci_flush_service(
        input_path,
        model_id=MODEL_ID,
        hydrant_node_ids=["J1", "J2"],
        hydrant_area_m2=0.002,
        total_loss_coefficient=2.0,
        velocity_threshold_mps=0.5,
        min_pressure_head_m=1.0,
    )

    assert (
        run_dir / "model.inp"
    ).read_bytes() == input_path.read_bytes()

    config = json.loads(
        (run_dir / "flushing_config.json").read_text(
            encoding="utf-8"
        )
    )

    assert config["hydrant_node_ids"] == ["J1", "J2"]
    assert config["output_dir"] == "results"
    assert config["min_pressure_head_m"] == 1.0

    assert result["success"] is True
    assert result["partial"] is False
    assert result["status"] == "success"
    assert result["run_id"] == RUN_ID
    assert result["model_id"] == MODEL_ID
    assert result["scenario_count"] == 2
    assert result["plan_count"] == 2
    assert [
        row["node_id"]
        for row in result["plan"]
    ] == ["J2", "J1"]
    assert (
        result["files"]["plan_csv"]
        == "results/flushing_plan.csv"
    )


def test_call_staci_flush_service_returns_partial_results(
    input_path: Path,
    run_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = run_root / "flushing" / RUN_ID

    def fake_run_staci_flush(
        inp_path: Path,
        config_path: Path,
    ) -> StaciFlushResults:
        output_dir = run_dir / "results"
        output_dir.mkdir()

        (output_dir / "run.json").write_text(
            json.dumps({"scenario_count": 2}),
            encoding="utf-8",
        )
        (output_dir / "scenarios.csv").write_text(
            "node_id,status\n"
            "J1,valid\n"
            "J2,invalid\n",
            encoding="utf-8",
        )
        (run_dir / "staci_flush.stdout.log").touch()
        (run_dir / "staci_flush.stderr.log").touch()

        return _flush_result(run_dir, returncode=3)

    monkeypatch.setattr(
        flushing_runner,
        "run_staci_flush",
        fake_run_staci_flush,
    )

    result = flushing_runner.call_staci_flush_service(
        input_path,
        model_id=MODEL_ID,
        hydrant_node_ids=["J1", "J2"],
        hydrant_area_m2=0.002,
        total_loss_coefficient=2.0,
        velocity_threshold_mps=0.5,
    )

    assert result["success"] is False
    assert result["partial"] is True
    assert result["status"] == "partial"
    assert result["scenario_count"] == 2
    assert result["plan"] == []


def test_call_staci_flush_service_rejects_failed_run(
    input_path: Path,
    run_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = run_root / "flushing" / RUN_ID
    run_result = _flush_result(run_dir, returncode=1)

    monkeypatch.setattr(
        flushing_runner,
        "run_staci_flush",
        lambda inp_path, config_path: run_result,
    )

    with pytest.raises(RuntimeError, match="return code 1"):
        flushing_runner.call_staci_flush_service(
            input_path,
            model_id=MODEL_ID,
            hydrant_node_ids=["J1"],
            hydrant_area_m2=0.002,
            total_loss_coefficient=2.0,
            velocity_threshold_mps=0.5,
        )


def test_call_staci_flush_service_rejects_invalid_hydrant_ids(
    input_path: Path,
    run_root: Path,
) -> None:
    with pytest.raises(ValueError, match="non-empty hydrant"):
        flushing_runner.call_staci_flush_service(
            input_path,
            model_id=MODEL_ID,
            hydrant_node_ids=[],
            hydrant_area_m2=0.002,
            total_loss_coefficient=2.0,
            velocity_threshold_mps=0.5,
        )

    with pytest.raises(ValueError, match="must be unique"):
        flushing_runner.call_staci_flush_service(
            input_path,
            model_id=MODEL_ID,
            hydrant_node_ids=["J1", "J1"],
            hydrant_area_m2=0.002,
            total_loss_coefficient=2.0,
            velocity_threshold_mps=0.5,
        )
        
def test_load_flushing_scenario_returns_selected_typed_rows(
    run_root: Path,
) -> None:
    results_dir = (
        run_root
        / "flushing"
        / RUN_ID
        / "results"
    )
    results_dir.mkdir(parents=True)

    (results_dir / "scenario_pipes.csv").write_text(
        (
            "hydrant_id,node_id,pipe_id,flow_m3s,"
            "velocity_mps,absolute_velocity_mps,"
            "baseline_velocity_mps,above_threshold,"
            "newly_above_threshold\n"
            "J1,J1,P1,0.01,-0.5,0.5,0.02,1,1\n"
            "J2,J2,P1,0.02,0.7,0.7,0.02,1,1\n"
        ),
        encoding="utf-8",
    )

    (
        results_dir / "scenario_hydrants.csv"
    ).write_text(
        (
            "scenario_id,node_id,status,flow_m3s,"
            "pressure_head_m\n"
            "J1,J1,ok,0.01,21.5\n"
            "J2,J2,ok,0.02,20.0\n"
        ),
        encoding="utf-8",
    )

    scenario = (
        flushing_runner.load_flushing_scenario(
            RUN_ID,
            "J1",
        )
    )

    assert scenario["run_id"] == RUN_ID
    assert scenario["scenario_id"] == "J1"

    assert scenario["hydrants"] == [
        {
            "node_id": "J1",
            "status": "ok",
            "flow_m3s": pytest.approx(0.01),
            "pressure_head_m": pytest.approx(21.5),
        }
    ]

    assert scenario["pipes"] == [
        {
            "pipe_id": "P1",
            "flow_m3s": pytest.approx(0.01),
            "velocity_mps": pytest.approx(-0.5),
            "absolute_velocity_mps": pytest.approx(0.5),
            "baseline_velocity_mps": pytest.approx(0.02),
            "above_threshold": True,
            "newly_above_threshold": True,
        }
    ]
