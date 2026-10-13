import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.config import STACI_SPLIT_EXECUTABLE
from src.services import partition_runner


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "net1.inp"
RUN_ID = "123456abcdef"
MODEL_ID = "012345abcdef"


@pytest.mark.integration
@pytest.mark.staci
def test_call_staci_split_service_runs_real_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = STACI_SPLIT_EXECUTABLE.resolve()
    if not executable.is_file():
        pytest.skip(
            "Real STACI Split executable is not available. "
            "Set STACI_SPLIT_EXECUTABLE to run this test."
        )

    run_root = tmp_path / "runs"
    monkeypatch.setattr(partition_runner, "RUN_ROOT", run_root)
    monkeypatch.setattr(
        partition_runner.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=f"{RUN_ID}ffff"),
    )

    result = partition_runner.call_staci_split_service(
        FIXTURE_PATH,
        model_id=MODEL_ID,
        optimizer_settings={
            "global_debug_level": 0,
            "n_comm": 3,
            "popsize": 8,
            "ngen": 10,
        },
        seed=12345,
    )

    run_dir = run_root / "partition" / RUN_ID
    copied_input = run_dir / "model.inp"
    settings_path = run_dir / "staci_split_settings.xml"
    membership_path = run_dir / "membership.txt"

    assert result["success"] is True
    assert result["run_id"] == RUN_ID
    assert result["model_id"] == MODEL_ID
    assert result["n_nodes"] > 0
    assert 1 <= result["n_communities"] <= 3
    assert len(result["node_community"]) == result["n_nodes"]
    assert sum(result["n_community_members"].values()) == result["n_nodes"]
    assert set(result["node_community"].values()) == set(
        result["n_community_members"]
    )
    assert {"10", "11", "12"}.issubset(result["node_community"])

    assert copied_input.read_bytes() == FIXTURE_PATH.read_bytes()
    assert membership_path.is_file()
    assert membership_path.stat().st_size > 0
    assert (run_dir / "staci_split.stdout.log").is_file()
    assert (run_dir / "staci_split.stderr.log").is_file()

    settings_root = ET.parse(settings_path).getroot()
    settings = {element.tag: element.text for element in settings_root}
    assert Path(settings["fname"]) == copied_input.resolve()    # type: ignore
    assert settings["n_comm"] == "3"
    assert settings["popsize"] == "8"
    assert settings["ngen"] == "10"
