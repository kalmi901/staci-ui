from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Sequence, TypedDict

from src.config import UPLOAD_ROOT


_UPLOAD_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")
_SNAPSHOT_NAME_PATTERN = re.compile(
    r"^snapshot_[0-9]{3}\.inp$"
)
_UNSAFE_FILENAME_PATTERN = re.compile(
    r"[^A-Za-z0-9_.-]+"
)


class StoredCalibrationSnapshot(TypedDict):
    period_index: int
    filename: str
    stored_filename: str
    size_bytes: int


class CalibrationSnapshotUpload(TypedDict):
    upload_id: str
    snapshots: list[StoredCalibrationSnapshot]


class CalibrationMeasurementUpload(TypedDict):
    upload_id: str
    filename: str
    size_bytes: int
    data: dict[str, Any]


def _safe_filename(filename: str) -> str:
    name = Path(
        (filename or "input.json").replace("\\", "/")
    ).name
    name = _UNSAFE_FILENAME_PATTERN.sub("_", name)
    return name or "input.json"


def _upload_dir(upload_id: str) -> Path:
    if not _UPLOAD_ID_PATTERN.fullmatch(upload_id):
        raise ValueError(f"Invalid calibration upload id: {upload_id!r}")

    root = (
        Path(UPLOAD_ROOT) / "calibration"
    ).resolve()
    upload_dir = (root / upload_id).resolve()

    if not upload_dir.is_relative_to(root):
        raise ValueError("Invalid calibration upload directory.")

    return upload_dir


def store_calibration_snapshots(
    files: Sequence[tuple[str, bytes]],
) -> CalibrationSnapshotUpload:
    if not files:
        raise ValueError("At least one calibration INP snapshot is required.")

    prepared: list[tuple[str, bytes]] = []

    for filename, file_bytes in files:
        safe_name = _safe_filename(filename)

        if not safe_name.lower().endswith(".inp"):
            raise ValueError(
                "Calibration snapshots must use the "
                f".inp extension: {safe_name}"
            )

        if not isinstance(file_bytes, bytes) or not file_bytes:
            raise ValueError(f"Calibration snapshot is empty: {safe_name}")

        prepared.append((safe_name, file_bytes))

    upload_id = uuid.uuid4().hex[:12]
    upload_dir = _upload_dir(upload_id)
    upload_dir.mkdir(parents=True, exist_ok=False)

    snapshots: list[StoredCalibrationSnapshot] = []

    for period_index, (filename, file_bytes) in enumerate(
        prepared
    ):
        stored_filename = f"snapshot_{period_index:03d}.inp"
        stored_path = upload_dir / stored_filename
        stored_path.write_bytes(file_bytes)

        snapshots.append(
            {
                "period_index": period_index,
                "filename": filename,
                "stored_filename": stored_filename,
                "size_bytes": len(file_bytes),
            }
        )

    return {
        "upload_id": upload_id,
        "snapshots": snapshots,
    }


def resolve_calibration_snapshots(
    upload_id: str,
    stored_filenames: Sequence[str],
) -> list[Path]:
    upload_dir = _upload_dir(upload_id)
    resolved: list[Path] = []

    for stored_filename in stored_filenames:
        if not _SNAPSHOT_NAME_PATTERN.fullmatch(
            stored_filename
        ):
            raise ValueError(
                "Invalid calibration snapshot filename: "
                f"{stored_filename!r}"
            )

        path = (upload_dir / stored_filename).resolve()

        if not path.is_relative_to(upload_dir):
            raise ValueError("Invalid calibration snapshot path.")

        if not path.is_file():
            raise FileNotFoundError(
                "Calibration snapshot does not exist: "
                f"{path}"
            )

        resolved.append(path)

    return resolved


def store_calibration_measurements(
    upload_id: str,
    filename: str,
    file_bytes: bytes,
) -> CalibrationMeasurementUpload:
    upload_dir = _upload_dir(upload_id)

    if not upload_dir.is_dir():
        raise FileNotFoundError(
            "Calibration upload does not exist: "
            f"{upload_dir}"
        )

    safe_name = _safe_filename(filename)

    if not safe_name.lower().endswith(".json"):
        raise ValueError("Calibration measurements must use JSON.")

    try:
        decoded = file_bytes.decode("utf-8-sig")
        data = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Calibration measurements contain invalid JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError(
            "Calibration measurements must contain "
            "a JSON object."
        )

    measurements = data.get("measurements")

    if not isinstance(measurements, list):
        raise ValueError(
            "Calibration JSON must contain a "
            "measurements array."
        )

    stored_path = upload_dir / "measurements.json"
    stored_path.write_text(
        json.dumps(
            data,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "upload_id": upload_id,
        "filename": safe_name,
        "size_bytes": len(file_bytes),
        "data": data,
    }