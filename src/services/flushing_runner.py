from __future__ import annotations

import csv
import json
import shutil
import uuid
from pathlib import Path
from typing import Any, Literal, Sequence

from src.config import RUN_ROOT
from src.staci.flush import run_staci_flush, write_flush_config


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
        },
    }