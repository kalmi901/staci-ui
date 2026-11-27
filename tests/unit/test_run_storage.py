from pathlib import Path

import pytest

from src.services import run_storage
from src.services.resource_ownership import write_resource_owner

VALID_RUN_ID = "abcdef012345"
OWNER_USER_ID = "41"
OTHER_USER_ID = "42"


@pytest.fixture
def run_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setattr(run_storage, "RUN_ROOT", root)
    return root


@pytest.mark.parametrize(
    "run_type", ["hydraulic", "partition", "flushing", "calibration"]
)
def test_resolve_run_dir_returns_path_for_supported_run_type(
    run_root: Path,
    run_type: str,
) -> None:
    run_dir = run_root / run_type / VALID_RUN_ID
    run_dir.mkdir(parents=True)
    write_resource_owner(
        run_dir,
        OWNER_USER_ID,
    )
    resolved_path = run_storage.resolve_run_dir(
        VALID_RUN_ID, run_type, user_id=OWNER_USER_ID
    )  # type: ignore[arg-type]

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
        run_storage.resolve_run_dir(run_id, "hydraulic", user_id=OWNER_USER_ID)


def test_resolve_run_dir_rejects_path_outside_run_root(
    run_root: Path,
) -> None:
    with pytest.raises(ValueError, match="Invalid run directory"):
        run_storage.resolve_run_dir(VALID_RUN_ID, "../../escape", user_id=OWNER_USER_ID)  # pyright: ignore[reportArgumentType]


def test_resolve_run_dir_rejects_other_user(
    run_root: Path,
) -> None:
    run_dir = run_root / "hydraulic" / VALID_RUN_ID
    run_dir.mkdir(parents=True)
    write_resource_owner(
        run_dir,
        OWNER_USER_ID,
    )

    with pytest.raises(
        PermissionError,
        match="not available for the current user",
    ):
        run_storage.resolve_run_dir(
            VALID_RUN_ID,
            "hydraulic",
            user_id=OTHER_USER_ID,
        )
