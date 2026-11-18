from __future__ import annotations

import pytest

from src.services.hydraulic_workload import (
    enforce_hydraulic_workload_limits,
    estimate_hydraulic_workload,
)


def test_estimate_hydraulic_workload() -> None:
    workload = estimate_hydraulic_workload(
        node_count=10,
        link_count=15,
        duration_seconds=7200,
        hydraulic_timestep_seconds=300,
        report_timestep_seconds=1800,
    )

    assert workload.hydraulic_steps == 24
    assert workload.report_frames == 5
    assert workload.work_units == 600


def test_zero_duration_still_requires_one_solve() -> None:
    workload = estimate_hydraulic_workload(
        node_count=10,
        link_count=15,
        duration_seconds=0,
        hydraulic_timestep_seconds=300,
        report_timestep_seconds=1800,
    )

    assert workload.hydraulic_steps == 1
    assert workload.report_frames == 1
    assert workload.work_units == 25


@pytest.mark.parametrize(
    ("limits", "expected_message"),
    [
        (
            {
                "max_hydraulic_steps": 9,
                "max_report_frames": 100,
                "max_work_units": 1000,
            },
            "hydraulic steps",
        ),
        (
            {
                "max_hydraulic_steps": 100,
                "max_report_frames": 10,
                "max_work_units": 1000,
            },
            "report frames",
        ),
        (
            {
                "max_hydraulic_steps": 100,
                "max_report_frames": 100,
                "max_work_units": 100,
            },
            "work units",
        ),
    ],
)
def test_enforce_hydraulic_workload_limits_rejects_excessive_runs(
    limits: dict[str, int],
    expected_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        enforce_hydraulic_workload_limits(
            node_count=6,
            link_count=5,
            duration_seconds=100,
            hydraulic_timestep_seconds=10,
            report_timestep_seconds=10,
            **limits,
        )


@pytest.mark.parametrize(
    (
        "duration_seconds",
        "hydraulic_timestep_seconds",
        "report_timestep_seconds",
        "expected_message",
    ),
    [
        (-1, 10, 10, "duration"),
        (100, 0, 10, "Hydraulic timestep"),
        (100, 10, 0, "Report timestep"),
    ],
)
def test_estimate_hydraulic_workload_rejects_invalid_timing(
    duration_seconds: float,
    hydraulic_timestep_seconds: float,
    report_timestep_seconds: float,
    expected_message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        estimate_hydraulic_workload(
            node_count=1,
            link_count=1,
            duration_seconds=duration_seconds,
            hydraulic_timestep_seconds=(hydraulic_timestep_seconds),
            report_timestep_seconds=(report_timestep_seconds),
        )
