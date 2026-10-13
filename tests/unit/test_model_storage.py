from pathlib import Path
from types import SimpleNamespace

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


def test_store_uploaded_model_writes_bytes_and_returns_metadata(
    upload_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        model_storage.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=f"{VALID_MODEL_ID}ffff"),
    )
    file_bytes = b"[TITLE]\nTest network\n"

    stored = model_storage.store_uploaded_model(
        "network.inp",
        file_bytes,
    )

    expected_path = upload_root / VALID_MODEL_ID / "network.inp"
    assert stored == {
        "model_id": VALID_MODEL_ID,
        "filename": "network.inp",
        "path": str(expected_path),
        "size_bytes": len(file_bytes),
    }
    assert expected_path.read_bytes() == file_bytes


def test_store_uploaded_model_sanitizes_filename_and_uses_only_name(
    upload_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        model_storage.uuid,
        "uuid4",
        lambda: SimpleNamespace(hex=f"{VALID_MODEL_ID}ffff"),
    )

    stored = model_storage.store_uploaded_model(
        "../../unsafe network!.inp",
        b"[TITLE]\n",
    )

    expected_path = upload_root / VALID_MODEL_ID / "unsafe_network_.inp"
    assert stored["filename"] == "unsafe_network_.inp"
    assert stored["path"] == str(expected_path)
    assert expected_path.is_file()


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