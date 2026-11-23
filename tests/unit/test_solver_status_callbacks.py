from __future__ import annotations

from typing import Any

from src.services.solver_jobs import (
    SolverJob,
    SolverQueueStatus,
)
from src.ui.callbacks.solver_status_callbacks import (
    render_solver_status,
)


def _component_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (list, tuple)):
        return " ".join(_component_text(item) for item in value)

    return _component_text(getattr(value, "children", None))


def test_render_solver_status_without_user_job() -> None:
    component = render_solver_status(
        SolverQueueStatus(
            capacity=2,
            running_jobs=0,
            queued_jobs=0,
            user_job=None,
            queue_position=None,
        )
    )

    text = _component_text(component)

    assert "Available" in text
    assert "0/2 solver slots active" in text
    assert "0 waiting" in text
    assert "You have no active solver job." in text


def test_render_solver_status_with_queued_user_job() -> None:
    component = render_solver_status(
        SolverQueueStatus(
            capacity=2,
            running_jobs=2,
            queued_jobs=1,
            user_job=SolverJob(
                token="token-a",
                user_id="41",
                workflow="calibration",
                state="queued",
                submitted_at=1000.0,
            ),
            queue_position=1,
        )
    )

    text = _component_text(component)

    assert "Busy" in text
    assert "Your pipe calibration job is waiting." in text
    assert "Queue position: 1." in text


def test_render_solver_status_with_running_user_job() -> None:
    component = render_solver_status(
        SolverQueueStatus(
            capacity=2,
            running_jobs=1,
            queued_jobs=0,
            user_job=SolverJob(
                token="token-a",
                user_id="41",
                workflow="hydraulic",
                state="running",
                submitted_at=1000.0,
                started_at=1001.0,
                celery_task_id="celery-task",
            ),
            queue_position=None,
        )
    )

    text = _component_text(component)

    assert "Available" in text
    assert "1/2 solver slots active" in text
    assert "Your hydraulic simulation job is running." in text
