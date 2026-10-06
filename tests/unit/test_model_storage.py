from pathlib import Path

import pytest

from src.services import model_storage


VALID_MODEL_ID = "012345abcdef"


@pytest.fixture
def upload_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "uploads"
    root.mkdir()
    monkeypatch.setattr(model_storage, "UPLOAD_ROOT", root)
    return root


def test_resolve_uploaded_model_returns_existing_model_path(
    upload_root: Path,
) -> None:
    model_directory = upload_root / VALID_MODEL_ID
    model_directory.mkdir()
    model_path = model_directory / "network.inp"
    model_path.write_text("[TITLE]\nTest network\n", encoding="utf-8")

    resolved_path = model_storage.resolve_uploaded_model(
        VALID_MODEL_ID,
        "network.inp",
    )

    assert resolved_path == model_path.resolve()


@pytest.mark.parametrize(
    "model_id",
    [
        "",
        "too-short",
        "0123456789abc",
        "012345ABCDEf",
        "../../escape",
    ],
)
def test_resolve_uploaded_model_rejects_invalid_model_id(
    upload_root: Path,
    model_id: str,
) -> None:
    with pytest.raises(ValueError, match="Invalid model id"):
        model_storage.resolve_uploaded_model(model_id, "network.inp")


def test_resolve_uploaded_model_rejects_missing_file(
    upload_root: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="Uploaded model does not exist"):
        model_storage.resolve_uploaded_model(VALID_MODEL_ID, "missing.inp")


def test_resolve_uploaded_model_uses_only_filename_component(
    upload_root: Path,
) -> None:
    model_directory = upload_root / VALID_MODEL_ID
    model_directory.mkdir()
    model_path = model_directory / "network.inp"
    model_path.write_text("[TITLE]\nTest network\n", encoding="utf-8")

    resolved_path = model_storage.resolve_uploaded_model(
        VALID_MODEL_ID,
        "../../network.inp",
    )

    assert resolved_path == model_path.resolve()