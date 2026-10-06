import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.config import STACI_EXECUTABLE
from src.services import hydraulic_runner


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tiny_network.inp"
RUN_ID = "fedcba543210"
MODEL_ID = "012345abcdef"


@pytest.mark.integration
@pytest.mark.staci
def test_call_hydraulic_simulator_runs_real_staci_eps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = STACI_EXECUTABLE.resolve()
    if not executable.is_file():
        pytest.skip(
            "Real STACI executable is not available. "
            "Set STACI_EXECUTABLE to run this test."
        )

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
        backend="staci",
    )

    run_dir = run_root / "hydraulic" / RUN_ID
    manifest_path = run_dir / "run.json"

    assert result["run_id"] == RUN_ID
    assert result["model_id"] == MODEL_ID
    assert result["backend"] == "staci"
    assert result["status"] == "success"
    assert result["summary"]["n_steps"] > 0
    assert len(result["time"]) == result["summary"]["n_steps"]
    assert result["time"][0] == 0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest == {
        "backend": "staci",
        "files": {
            "hdf5": "results.h5",
            "metadata": "results.meta.json",
            "stdout": "staci.stdout.log",
            "stderr": "staci.stderr.log",
        },
    }

    h5_path = run_dir / manifest["files"]["hdf5"]
    metadata_path = run_dir / manifest["files"]["metadata"]
    stdout_path = run_dir / manifest["files"]["stdout"]
    stderr_path = run_dir / manifest["files"]["stderr"]

    assert h5_path.is_file()
    assert h5_path.stat().st_size > 0
    assert metadata_path.is_file()
    assert stdout_path.is_file()
    assert stderr_path.is_file()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["simulation"]["status"] == "complete"