from __future__ import annotations

import json
import math
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from src.config import (
    RUN_ROOT,
    STACI_CALIBRATE_EXECUTABLE,
)
from src.results.calibration import (
    parse_calibration_best,
    parse_calibration_history,
)
from src.run_logging import log_prepared_input
from src.services.inp_model_reader import (
    read_water_network_model,
)
from src.services.run_storage import resolve_run_dir
from src.staci.calibrate import (
    run_staci_calibrate,
    write_calibrate_settings,
)


@dataclass(frozen=True)
class _NetworkTopology:
    nodes: tuple[tuple[str, str], ...]
    links: tuple[tuple[str, str, str, str], ...]


def _read_topology(path: Path) -> _NetworkTopology:
    model = read_water_network_model(path)

    try:
        nodes = model["nodes"]
        links = model["links"]

        node_topology = tuple(
            (str(node_id), str(node_type))
            for node_id, node_type in zip(
                nodes["id"],
                nodes["type"],
                strict=True,
            )
        )

        link_topology = tuple(
            (
                str(link_id),
                str(link_type),
                str(start_node),
                str(end_node),
            )
            for (
                link_id,
                link_type,
                start_node,
                end_node,
            ) in zip(
                links["id"],
                links["type"],
                links["start_node"],
                links["end_node"],
                strict=True,
            )
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"Could not read calibration topology from {path}."
        ) from exc

    return _NetworkTopology(
        nodes=node_topology,
        links=link_topology,
    )


def _validate_snapshot_topologies(
    snapshot_paths: Sequence[Path],
) -> None:
    reference_path = snapshot_paths[0]
    reference = _read_topology(reference_path)

    for period_index, snapshot_path in enumerate(
        snapshot_paths[1:],
        start=1,
    ):
        candidate = _read_topology(snapshot_path)
        differences: list[str] = []

        if candidate.nodes != reference.nodes:
            differences.append("node IDs, ordering, or types")

        if candidate.links != reference.links:
            differences.append(
                "link IDs, ordering, types, or endpoints"
            )

        if differences:
            raise ValueError(
                "Calibration snapshot "
                f"{period_index} ({snapshot_path.name}) is not "
                f"topologically compatible with period 0 "
                f"({reference_path.name}): "
                + "; ".join(differences)
                + "."
            )


def _normalise_measurements(
    measurements: dict[str, Any],
    snapshot_count: int,
) -> dict[str, Any]:
    if not isinstance(measurements, dict):
        raise ValueError(
            "Calibration measurements must be a JSON object."
        )

    rows = measurements.get("measurements")

    if not isinstance(rows, list) or not rows:
        raise ValueError(
            "Calibration measurements must contain a "
            "non-empty measurements array."
        )

    normalised_rows: list[dict[str, Any]] = []
    measurement_ids: set[str] = set()

    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(
                f"Calibration measurement row {row_index} "
                "must be an object."
            )

        measurement_id = row.get("id")
        measurement_type = row.get("type")
        values = row.get("values")

        if (
            not isinstance(measurement_id, str)
            or not measurement_id.strip()
        ):
            raise ValueError(
                f"Calibration measurement row {row_index} "
                "requires a non-empty id."
            )

        measurement_id = measurement_id.strip()

        if measurement_id in measurement_ids:
            raise ValueError(
                "Calibration measurement IDs must be unique: "
                f"{measurement_id!r}."
            )

        if (
            not isinstance(measurement_type, str)
            or measurement_type.lower() not in {"node", "pool"}
        ):
            raise ValueError(
                f"Calibration measurement {measurement_id!r} "
                "must have type 'node' or 'pool'."
            )

        if (
            not isinstance(values, list)
            or len(values) != snapshot_count
        ):
            raise ValueError(
                f"Calibration measurement {measurement_id!r} "
                f"must contain exactly {snapshot_count} values."
            )

        normalised_values: list[float] = []

        for period_index, value in enumerate(values):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise ValueError(
                    f"Calibration measurement "
                    f"{measurement_id!r}, period "
                    f"{period_index}, must be a finite number."
                )

            normalised_values.append(float(value))

        measurement_ids.add(measurement_id)
        normalised_rows.append(
            {
                "id": measurement_id,
                "type": measurement_type.lower(),
                "values": normalised_values,
            }
        )

    return {"measurements": normalised_rows}


def _relative_path(path: Path, run_dir: Path) -> str:
    return path.relative_to(run_dir).as_posix()


def call_staci_calibrate_service(
    snapshot_paths: Sequence[Path | str],
    *,
    measurements: dict[str, Any],
    optimizer_settings: dict[str, Any] | None = None,
    seed: int = 12345,
) -> dict[str, Any]:
    if isinstance(snapshot_paths, (str, Path)):
        raise ValueError(
            "Calibration snapshots must be supplied as a sequence."
        )

    source_paths = [
        Path(path).resolve()
        for path in snapshot_paths
    ]

    if not source_paths:
        raise ValueError(
            "At least one calibration INP snapshot is required."
        )

    for snapshot_path in source_paths:
        if not snapshot_path.is_file():
            raise FileNotFoundError(
                "Calibration INP snapshot does not exist: "
                f"{snapshot_path}"
            )

        if snapshot_path.suffix.lower() != ".inp":
            raise ValueError(
                "Calibration snapshots must use the .inp "
                f"extension: {snapshot_path}"
            )

    if len(set(source_paths)) != len(source_paths):
        raise ValueError(
            "Calibration snapshot paths must be unique."
        )

    normalised_measurements = _normalise_measurements(
        measurements,
        len(source_paths),
    )

    # Validate before allocating a run directory, so invalid uploads
    # do not leave an abandoned run.
    _validate_snapshot_topologies(source_paths)

    run_id = uuid.uuid4().hex[:12]
    run_dir = Path(RUN_ROOT) / "calibration" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    stored_snapshots: list[Path] = []
    snapshot_state: list[dict[str, Any]] = []

    for period_index, source_path in enumerate(source_paths):
        stored_path = run_dir / f"network_{period_index}.inp"
        shutil.copy2(source_path, stored_path)
        stored_snapshots.append(stored_path)

        snapshot_state.append(
            {
                "period_index": period_index,
                "source_filename": source_path.name,
                "stored_filename": stored_path.name,
            }
        )

    measurements_path = run_dir / "measurements.json"
    measurements_path.write_text(
        json.dumps(
            normalised_measurements,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    settings_path = run_dir / "staci_calibrate_settings.json"

    write_calibrate_settings(
        settings_path,
        measurements_path=measurements_path,
        snapshot_count=len(stored_snapshots),
        overrides=optimizer_settings,
    )

    # Follow the existing solver-service logging convention.
    log_prepared_input(
        stored_snapshots[0],
        run_id,
        settings_path=settings_path,
        executable=STACI_CALIBRATE_EXECUTABLE,
    )

    result = run_staci_calibrate(
        settings_path,
        seed=seed,
    )

    if not result.success:
        raise RuntimeError(
            "STACI Calibrate did not complete successfully "
            f"(return code {result.returncode}). "
            f"See {result.stderr_path}"
        )

    best = parse_calibration_best(result.best_data_path)
    history = parse_calibration_history(result.history_path)

    pipes = [asdict(pipe)for pipe in best.pipes]
    comparisons = [asdict(comparison)for comparison in best.comparisons]
    history_entries = [asdict(entry) for entry in history]

    manifest_path = run_dir / "run.json"

    run_state: dict[str, Any] = {
        "success": True,
        "status": "success",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "snapshots": snapshot_state,
        "summary": {
            "snapshot_count": len(stored_snapshots),
            "measurement_count": len(
                normalised_measurements["measurements"]
            ),
            "calibrated_pipe_count": len(pipes),
            "comparison_count": len(comparisons),
            "history_point_count": len(history_entries),
        },
        "pipes": pipes,
        "comparisons": comparisons,
        "history": history_entries,
        "files": {
            "manifest": manifest_path.name,
            "snapshots": [
                path.name
                for path in stored_snapshots
            ],
            "measurements": measurements_path.name,
            "settings": settings_path.name,
            "best": _relative_path(result.best_data_path, run_dir),
            "history": _relative_path(result.history_path, run_dir),
            "stdout": _relative_path(result.stdout_path, run_dir),
            "stderr": _relative_path(result.stderr_path, run_dir),
            "diagnostics": _relative_path(result.diagnostics_path, run_dir),
            "calibration_log": _relative_path(result.calibration_log_path, run_dir),
            "best_log": _relative_path(result.best_log_path, run_dir),
            "sensitivity_mass_flow": _relative_path(result.sensitivity_mass_flow_path, run_dir),
            "sensitivity_pressure": _relative_path(result.sensitivity_pressure_path, run_dir),
        },
    }

    manifest_path.write_text(
        json.dumps(
            run_state,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return run_state


def load_calibration_run(run_id: str) -> dict[str, Any]:
    run_dir = resolve_run_dir(
        run_id,
        "calibration",
    )
    manifest_path = run_dir / "run.json"

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Calibration run manifest not found: "
            f"{manifest_path}"
        )

    run_state = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if not isinstance(run_state, dict):
        raise ValueError(
            f"Invalid calibration run manifest: {manifest_path}"
        )

    return run_state