from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

from src.config import (
    STACI_FLUSH_EXECUTABLE,
    STACI_TIMEOUT_SECONDS,
)
from src.staci.runtime import _stream_to_text


@dataclass(frozen=True)
class StaciFlushResults:
    returncode: int
    output_dir: Path
    stdout_path: Path
    stderr_path: Path
    run_json_path: Path
    scenarios_path: Path
    plan_csv_path: Path
    plan_text_path: Path
    pipe_travel_times_path: Path
    pipes_above_threshold_path: Path
    pipe_coverage_path: Path
    scenario_hydrants_path: Path
    scenario_pipes_path: Path

    @property
    def success(self) -> bool:
        return (
            self.returncode == 0
            and self.run_json_path.is_file()
            and self.scenarios_path.is_file()
            and self.plan_csv_path.is_file()
        )

    @property
    def partial(self) -> bool:
        return (
            self.returncode == 3
            and self.run_json_path.is_file()
            and self.scenarios_path.is_file()
        )


def write_flush_config(
    output_path: Path,
    *,
    hydrant_node_ids: Sequence[str],
    hydrant_area_m2: float,
    total_loss_coefficient: float,
    velocity_threshold_mps: float,
    output_dir: Path | str,
    mode: Literal["single", "multi"] = "single",
    min_pressure_head_m: float = 0.0,
    write_network_files: bool = False,
) -> None:
    config = {
        "mode": mode,
        "hydrant_node_ids": list(hydrant_node_ids),
        "hydrant_area_m2": hydrant_area_m2,
        "total_loss_coefficient": total_loss_coefficient,
        "velocity_threshold_mps": velocity_threshold_mps,
        "min_pressure_head_m": min_pressure_head_m,
        "output_dir": str(output_dir),
        "write_network_files": write_network_files,
    }

    output_path.write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )


def _resolve_output_dir(config_path: Path) -> Path:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir_value = config.get("output_dir")

    if not isinstance(output_dir_value, str) or not output_dir_value.strip():
        raise ValueError(
            "STACI Flush configuration must contain a non-empty "
            "string output_dir."
        )

    output_dir = Path(output_dir_value).expanduser()
    if not output_dir.is_absolute():
        output_dir = config_path.parent / output_dir

    return output_dir.resolve()


def run_staci_flush(
    inp_path: Path,
    config_path: Path,
) -> StaciFlushResults:
    if not STACI_FLUSH_EXECUTABLE.is_file():
        raise FileNotFoundError(
            f"STACI Flush executable not found: {STACI_FLUSH_EXECUTABLE}"
        )

    inp_path = inp_path.resolve()
    config_path = config_path.resolve()

    if not inp_path.is_file():
        raise FileNotFoundError(
            f"STACI Flush input file not found: {inp_path}"
        )

    if not config_path.is_file():
        raise FileNotFoundError(
            f"STACI Flush configuration file not found: {config_path}"
        )

    run_dir = config_path.parent
    output_dir = _resolve_output_dir(config_path)
    stdout_path = run_dir / "staci_flush.stdout.log"
    stderr_path = run_dir / "staci_flush.stderr.log"

    command = [
        str(STACI_FLUSH_EXECUTABLE),
        "--inp",
        str(inp_path),
        "--config",
        str(config_path),
    ]

    try:
        result = subprocess.run(
            command,
            cwd=run_dir,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=STACI_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(
            _stream_to_text(exc.stdout),
            encoding="utf-8",
        )
        stderr_path.write_text(
            _stream_to_text(exc.stderr),
            encoding="utf-8",
        )
        raise TimeoutError(
            f"STACI Flush exceeded the "
            f"{STACI_TIMEOUT_SECONDS} s timeout."
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"STACI Flush execution failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    stdout_path.write_text(result.stdout or "", encoding="utf-8")
    stderr_path.write_text(result.stderr or "", encoding="utf-8")

    return StaciFlushResults(
        returncode=result.returncode,
        output_dir=output_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        run_json_path=output_dir / "run.json",
        scenarios_path=output_dir / "scenarios.csv",
        plan_csv_path=output_dir / "flushing_plan.csv",
        plan_text_path=output_dir / "flushing_plan.txt",
        pipe_travel_times_path=output_dir / "pipe_travel_times.csv",
        pipes_above_threshold_path=output_dir / "pipes_above_threshold.csv",
        pipe_coverage_path=output_dir / "pipe_coverage.csv",
        scenario_hydrants_path=output_dir / "scenario_hydrants.csv",
        scenario_pipes_path=output_dir / "scenario_pipes.csv"
    )