from __future__ import annotations

import csv
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Literal, Sequence

from src.config import RUN_ROOT
from src.staci.flush import run_staci_flush, write_flush_config
from src.services.run_storage import resolve_run_dir


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []

    with path.open(encoding="utf-8", newline="") as csv_file:
        return [dict(row) for row in csv.DictReader(csv_file)]


def _read_run_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"Invalid STACI Flush run manifest: {path}")

    return manifest


def _required_float(
    row: dict[str, str],
    field: str,
) -> float:
    try:
        return float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid or missing CSV field: {field}"
        ) from exc


def _flag(
    row: dict[str, str],
    field: str,
) -> bool:
    try:
        value = row[field]
    except KeyError as exc:
        raise ValueError(
            f"Missing CSV field: {field}"
        ) from exc

    if value == "1":
        return True

    if value == "0":
        return False

    raise ValueError(
        f"Invalid CSV flag {field}: {value!r}"
    )


def load_flushing_scenario(
    run_id: str,
    scenario_id: str,
) -> dict[str, Any]:
    if not scenario_id:
        raise ValueError(
            "Flushing scenario id is required."
        )

    run_dir = resolve_run_dir(
        run_id,
        "flushing",
    )
    results_dir = run_dir / "results"

    pipe_path = results_dir / "scenario_pipes.csv"
    hydrant_path = (
        results_dir / "scenario_hydrants.csv"
    )

    if not pipe_path.is_file():
        raise FileNotFoundError(
            f"Scenario pipe results not found: {pipe_path}"
        )

    if not hydrant_path.is_file():
        raise FileNotFoundError(
            "Scenario hydrant results not found: "
            f"{hydrant_path}"
        )

    pipes: list[dict[str, Any]] = []

    with pipe_path.open(
        encoding="utf-8",
        newline="",
    ) as csv_file:
        for row in csv.DictReader(csv_file):
            if row.get("hydrant_id") != scenario_id:
                continue

            pipes.append(
                {
                    "pipe_id": row.get("pipe_id", ""),
                    "flow_m3s": _required_float(
                        row,
                        "flow_m3s",
                    ),
                    "velocity_mps": _required_float(
                        row,
                        "velocity_mps",
                    ),
                    "absolute_velocity_mps": (
                        _required_float(
                            row,
                            "absolute_velocity_mps",
                        )
                    ),
                    "baseline_velocity_mps": (
                        _required_float(
                            row,
                            "baseline_velocity_mps",
                        )
                    ),
                    "above_threshold": _flag(
                        row,
                        "above_threshold",
                    ),
                    "newly_above_threshold": _flag(
                        row,
                        "newly_above_threshold",
                    ),
                }
            )

    hydrants: list[dict[str, Any]] = []

    with hydrant_path.open(
        encoding="utf-8",
        newline="",
    ) as csv_file:
        for row in csv.DictReader(csv_file):
            if row.get("scenario_id") != scenario_id:
                continue

            hydrants.append(
                {
                    "node_id": row.get("node_id", ""),
                    "status": row.get("status", ""),
                    "flow_m3s": _required_float(
                        row,
                        "flow_m3s",
                    ),
                    "pressure_head_m": _required_float(
                        row,
                        "pressure_head_m",
                    ),
                }
            )

    if not pipes and not hydrants:
        raise ValueError(
            f"Flushing scenario {scenario_id!r} "
            f"was not found in run {run_id}."
        )

    return {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "pipes": pipes,
        "hydrants": hydrants,
    }


def call_staci_flush_service(
    inp_path: Path | str,
    *,
    model_id: str,
    hydrant_node_ids: Sequence[str],
    hydrant_area_m2: float,
    total_loss_coefficient: float,
    velocity_threshold_mps: float,
    mode: Literal["single", "multi"] = "single",
    min_pressure_head_m: float = 0.0,
    write_network_files: bool = False,
) -> dict[str, Any]:
    inp_path = Path(inp_path)
    if not inp_path.is_file():
        raise FileNotFoundError(f"INP file does not exist: {inp_path}")

    hydrant_ids = [
        node_id.strip()
        for node_id in hydrant_node_ids
    ]

    if not hydrant_ids or any(not node_id for node_id in hydrant_ids):
        raise ValueError(
            "At least one non-empty hydrant node id is required."
        )

    if len(set(hydrant_ids)) != len(hydrant_ids):
        raise ValueError("Hydrant node ids must be unique.")

    run_id = uuid.uuid4().hex[:12]
    run_dir = Path(RUN_ROOT) / "flushing" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    run_inp = run_dir / "model.inp"
    shutil.copy2(inp_path, run_inp)

    config_path = run_dir / "flushing_config.json"

    write_flush_config(
        config_path,
        hydrant_node_ids=hydrant_ids,
        hydrant_area_m2=hydrant_area_m2,
        total_loss_coefficient=total_loss_coefficient,
        velocity_threshold_mps=velocity_threshold_mps,
        output_dir="results",
        mode=mode,
        min_pressure_head_m=min_pressure_head_m,
        write_network_files=write_network_files,
    )

    flush_result = run_staci_flush(run_inp, config_path)

    if not flush_result.success and not flush_result.partial:
        raise RuntimeError(
            "STACI Flush did not complete successfully "
            f"(return code {flush_result.returncode}). "
            f"See {flush_result.stderr_path}"
        )

    manifest = _read_run_manifest(flush_result.run_json_path)
    scenarios = _read_csv_rows(flush_result.scenarios_path)
    plan = _read_csv_rows(flush_result.plan_csv_path)

    return {
        "success": flush_result.success,
        "partial": flush_result.partial,
        "status": (
            "success"
            if flush_result.success
            else "partial"
        ),
        "run_id": run_id,
        "model_id": model_id,
        "mode": mode,
        "returncode": flush_result.returncode,
        "scenario_count": manifest.get(
            "scenario_count",
            len(scenarios),
        ),
        "plan_count": len(plan),
        "scenarios": scenarios,
        "plan": plan,
        "files": {
            "run": flush_result.run_json_path.relative_to(
                run_dir
            ).as_posix(),
            "scenarios": flush_result.scenarios_path.relative_to(
                run_dir
            ).as_posix(),
            "plan_csv": flush_result.plan_csv_path.relative_to(
                run_dir
            ).as_posix(),
            "plan_text": flush_result.plan_text_path.relative_to(
                run_dir
            ).as_posix(),
            "stdout": flush_result.stdout_path.relative_to(
                run_dir
            ).as_posix(),
            "stderr": flush_result.stderr_path.relative_to(
                run_dir
            ).as_posix(),
            "scenario_hydrants": flush_result.scenario_hydrants_path.relative_to(
                run_dir
            ).as_posix(),
            "scenario_pipes": flush_result.scenario_pipes_path.relative_to(
            run_dir
            ).as_posix(),
        },
    }