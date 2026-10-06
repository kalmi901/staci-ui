from pathlib import Path

import pytest

from src.services import run_storage


VALID_RUN_ID = "abcdef012345"


@pytest.fixture
def run_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setattr(run_storage, "RUN_ROOT", root)
    return root


@pytest.mark.parametrize("run_type", ["hydraulic", "partition"])
def test_resolve_run_dir_returns_path_for_supported_run_type(
    run_root: Path,
    run_type: str,
) -> None:
    resolved_path = run_storage.resolve_run_dir(VALID_RUN_ID, run_type)

    assert resolved_path == (run_root / run_type / VALID_RUN_ID).resolve()


@pytest.mark.parametrize(
    "run_id",
    [
        "",
        "too-short",
        "abcdef0123456",
        "ABCDEF012345",
        "../../escape",
    ],
)
def test_resolve_run_dir_rejects_invalid_run_id(
    run_root: Path,
    run_id: str,
) -> None:
    with pytest.raises(ValueError, match="Invalid run id"):
        run_storage.resolve_run_dir(run_id, "hydraulic")


def test_resolve_run_dir_rejects_path_outside_run_root(
    run_root: Path,
) -> None:
    with pytest.raises(ValueError, match="Invalid run directory"):
        run_storage.resolve_run_dir(VALID_RUN_ID, "../../escape")