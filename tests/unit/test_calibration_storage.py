import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services import calibration_storage


UPLOAD_ID = "123456abcdef"


@pytest.fixture
def upload_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    root = tmp_path / "uploads"

    monkeypatch.setattr(
        calibration_storage,
        "UPLOAD_ROOT",
        root,
    )
    monkeypatch.setattr(
        calibration_storage.uuid,
        "uuid4",
        lambda: SimpleNamespace(
            hex=f"{UPLOAD_ID}ffff"
        ),
    )

    return root


def test_store_calibration_snapshots_persists_ordered_inputs(
    upload_root: Path,
) -> None:
    state = (
        calibration_storage.store_calibration_snapshots(
            [
                ("first network.inp", b"period-zero"),
                ("second.inp", b"period-one"),
            ]
        )
    )

    assert state["upload_id"] == UPLOAD_ID
    assert [
        item["period_index"]
        for item in state["snapshots"]
    ] == [0, 1]
    assert [
        item["filename"]
        for item in state["snapshots"]
    ] == [
        "first_network.inp",
        "second.inp",
    ]

    paths = (
        calibration_storage.resolve_calibration_snapshots(
            UPLOAD_ID,
            [
                item["stored_filename"]
                for item in state["snapshots"]
            ],
        )
    )

    assert paths[0].read_bytes() == b"period-zero"
    assert paths[1].read_bytes() == b"period-one"


def test_store_calibration_snapshots_rejects_non_inp(
    upload_root: Path,
) -> None:
    with pytest.raises(ValueError, match=".inp"):
        calibration_storage.store_calibration_snapshots(
            [("network.txt", b"invalid")]
        )


def test_store_calibration_measurements_persists_json(
    upload_root: Path,
) -> None:
    calibration_storage.store_calibration_snapshots(
        [("network.inp", b"network")]
    )

    data = {
        "measurements": [
            {
                "id": "J1",
                "type": "node",
                "values": [30.0],
            }
        ]
    }

    state = (
        calibration_storage.store_calibration_measurements(
            UPLOAD_ID,
            "measurements.json",
            json.dumps(data).encode("utf-8"),
        )
    )

    assert state["data"] == data

    stored = (
        upload_root
        / "calibration"
        / UPLOAD_ID
        / "measurements.json"
    )
    assert json.loads(
        stored.read_text(encoding="utf-8")
    ) == data


def test_resolve_calibration_snapshots_rejects_unsafe_name(
    upload_root: Path,
) -> None:
    calibration_storage.store_calibration_snapshots(
        [("network.inp", b"network")]
    )

    with pytest.raises(
        ValueError,
        match="snapshot filename",
    ):
        calibration_storage.resolve_calibration_snapshots(
            UPLOAD_ID,
            ["../../escape.inp"],
        )