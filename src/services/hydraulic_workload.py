from __future__ import annotations

import math
from dataclasses import dataclass

from src.config import (
    MAX_HYDRAULIC_REPORT_FRAMES,
    MAX_HYDRAULIC_STEPS,
    MAX_HYDRAULIC_WORK_UNITS,
)


@dataclass(frozen=True)
class HydraulicWorkload:
    hydraulic_steps: int
    report_frames: int
    work_units: int


def estimate_hydraulic_workload(
    *,
    node_count: int,
    link_count: int,
    duration_seconds: float,
    hydraulic_timestep_seconds: float,
    report_timestep_seconds: float,
) -> HydraulicWorkload:
    if node_count < 0 or link_count < 0:
        raise ValueError("Network element counts must be non-negative.")

    if duration_seconds < 0:
        raise ValueError("Simulation duration must be non-negative.")

    if hydraulic_timestep_seconds <= 0:
        raise ValueError("Hydraulic timestep must be greater than zero.")

    if report_timestep_seconds <= 0:
        raise ValueError("Report timestep must be greater than zero.")

    hydraulic_steps = max(
        1,
        math.ceil(duration_seconds / hydraulic_timestep_seconds),
    )

    report_frames = math.ceil(duration_seconds / report_timestep_seconds) + 1

    work_units = (node_count + link_count) * hydraulic_steps

    return HydraulicWorkload(
        hydraulic_steps=hydraulic_steps,
        report_frames=report_frames,
        work_units=work_units,
    )


def enforce_hydraulic_workload_limits(
    *,
    node_count: int,
    link_count: int,
    duration_seconds: float,
    hydraulic_timestep_seconds: float,
    report_timestep_seconds: float,
    max_hydraulic_steps: int = MAX_HYDRAULIC_STEPS,
    max_report_frames: int = MAX_HYDRAULIC_REPORT_FRAMES,
    max_work_units: int = MAX_HYDRAULIC_WORK_UNITS,
) -> HydraulicWorkload:
    workload = estimate_hydraulic_workload(
        node_count=node_count,
        link_count=link_count,
        duration_seconds=duration_seconds,
        hydraulic_timestep_seconds=(hydraulic_timestep_seconds),
        report_timestep_seconds=(report_timestep_seconds),
    )

    violations: list[str] = []

    if workload.hydraulic_steps > max_hydraulic_steps:
        violations.append(
            f"hydraulic steps ({workload.hydraulic_steps:,} > {max_hydraulic_steps:,})"
        )

    if workload.report_frames > max_report_frames:
        violations.append(
            f"report frames ({workload.report_frames:,} > {max_report_frames:,})"
        )

    if workload.work_units > max_work_units:
        violations.append(f"work units ({workload.work_units:,} > {max_work_units:,})")

    if violations:
        raise ValueError(
            "Hydraulic simulation exceeds the server "
            "workload limit: "
            + "; ".join(violations)
            + ". Reduce the simulation duration, increase "
            "the hydraulic or report timestep, or use a "
            "smaller network."
        )

    return workload
