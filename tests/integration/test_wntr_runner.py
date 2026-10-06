import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services import hydraulic_runner


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tiny_network.inp"
RUN_ID = "abcdef012345"
MODEL_ID = "012345abcdef"


@pytest.mark.integration
def test_call_hydraulic_simulator_runs_wntr_and_writes_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root = tmp_path / "runs"
    monkeypatch.setattr(hydraulic_runner, "RUN_ROOT", run_root)
    monkeypatch.setattr(
        hydraulic_runner.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=f"{RUN_ID}ffff"),
    )

    result = hydraulic_runner.call_hydraulic_simulator(
        FIXTURE_PATH,
        model_id=MODEL_ID,
        backend="wntr",
    )

    run_dir = run_root / "hydraulic" / RUN_ID
    copied_input = run_dir / "input.inp"
    manifest_path = run_dir / "run.json"

    assert result["run_id"] == RUN_ID
    assert result["model_id"] == MODEL_ID
    assert result["backend"] == "wntr"
    assert result["status"] == "success"
    assert result["time"] == [0, 3600]
    assert result["summary"] == {
        "duration_seconds": 3600,
        "n_steps": 2,
    }
    assert copied_input.read_bytes() == FIXTURE_PATH.read_bytes()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest == {
        "backend": "wntr",
        "files": {
            "nodes": {
                "head": "node_head.csv",
                "pressure": "node_pressure.csv",
                "demand": "node_demand.csv",
            },
            "links": {
                "flowrate": "link_flowrate.csv",
                "velocity": "link_velocity.csv",
                "status": "link_status.csv",
            },
        },
    }

    result_files = [
        filename
        for group in manifest["files"].values()
        for filename in group.values()
    ]
    for filename in result_files:
        path = run_dir / filename
        assert path.is_file()
        assert path.stat().st_size > 0