from __future__ import annotations

from collections.abc import Iterator

import fakeredis
import pytest

from src.services.solver_jobs import (
    ActiveSolverJobError,
    SolverJobCancelledError,
    SolverJobRegistry,
)


@pytest.fixture
def token_values() -> Iterator[str]:
    return iter(
        [
            "token-a",
            "token-b",
            "token-c",
            "token-d",
        ]
    )


@pytest.fixture
def registry(
    token_values: Iterator[str],
) -> SolverJobRegistry:
    return SolverJobRegistry(
        fakeredis.FakeRedis(decode_responses=True),
        ttl_seconds=3600,
        capacity=2,
        clock=lambda: 1000.0,
        token_factory=lambda: next(token_values),
        key_prefix="test:solver",
    )


def test_submit_creates_queued_job(
    registry: SolverJobRegistry,
) -> None:
    job = registry.submit(
        user_id="41",
        workflow="hydraulic",
    )

    assert job.token == "token-a"
    assert job.user_id == "41"
    assert job.workflow == "hydraulic"
    assert job.state == "queued"

    status = registry.status_for_user("41")

    assert status.capacity == 2
    assert status.running_jobs == 0
    assert status.queued_jobs == 1
    assert status.user_job == job
    assert status.queue_position == 1


def test_submit_rejects_second_job_for_same_user(
    registry: SolverJobRegistry,
) -> None:
    first = registry.submit(
        user_id="41",
        workflow="hydraulic",
    )

    with pytest.raises(
        ActiveSolverJobError,
        match="queued hydraulic",
    ) as error:
        registry.submit(
            user_id="41",
            workflow="partition",
        )

    assert error.value.job == first


def test_queue_positions_follow_submission_order(
    registry: SolverJobRegistry,
) -> None:
    first = registry.submit(
        user_id="41",
        workflow="hydraulic",
    )
    second = registry.submit(
        user_id="42",
        workflow="partition",
    )

    assert first.token == "token-a"
    assert second.token == "token-b"

    assert registry.status_for_user("41").queue_position == 1
    assert registry.status_for_user("42").queue_position == 2


def test_mark_running_updates_queue_counts(
    registry: SolverJobRegistry,
) -> None:
    job = registry.submit(
        user_id="41",
        workflow="flushing",
    )

    running = registry.mark_running(
        token=job.token,
        user_id="41",
        celery_task_id="celery-123",
    )

    assert running.state == "running"
    assert running.started_at == 1000.0
    assert running.celery_task_id == "celery-123"

    status = registry.status_for_user("41")

    assert status.running_jobs == 1
    assert status.queued_jobs == 0
    assert status.queue_position is None
    assert status.user_job == running


def test_finish_releases_user_slot(
    registry: SolverJobRegistry,
) -> None:
    first = registry.submit(
        user_id="41",
        workflow="calibration",
    )

    registry.mark_running(
        token=first.token,
        user_id="41",
        celery_task_id="celery-123",
    )

    finished = registry.finish(
        token=first.token,
        user_id="41",
        state="completed",
    )

    assert finished is not None
    assert finished.state == "completed"

    status = registry.status_for_user("41")

    assert status.running_jobs == 0
    assert status.queued_jobs == 0
    assert status.user_job is None

    second = registry.submit(
        user_id="41",
        workflow="hydraulic",
    )

    assert second.token == "token-b"


def test_job_cannot_be_changed_by_another_user(
    registry: SolverJobRegistry,
) -> None:
    job = registry.submit(
        user_id="41",
        workflow="hydraulic",
    )

    with pytest.raises(
        PermissionError,
        match="another user",
    ):
        registry.mark_running(
            token=job.token,
            user_id="42",
            celery_task_id="celery-123",
        )

    with pytest.raises(
        PermissionError,
        match="another user",
    ):
        registry.finish(
            token=job.token,
            user_id="42",
            state="failed",
        )


def test_cancel_running_job_preserves_cancelled_state(
    registry: SolverJobRegistry,
) -> None:
    job = registry.submit(
        user_id="41",
        workflow="hydraulic",
    )
    registry.mark_running(
        token=job.token,
        user_id="41",
        celery_task_id="celery-123",
    )

    cancelled = registry.cancel_user_job("41")

    assert cancelled is not None
    assert cancelled.state == "cancelled"
    assert registry.status_for_user("41").user_job is None

    finished = registry.finish(
        token=job.token,
        user_id="41",
        state="failed",
    )

    assert finished is not None
    assert finished.state == "cancelled"


def test_cancel_queued_job_prevents_execution(
    registry: SolverJobRegistry,
) -> None:
    job = registry.submit(
        user_id="41",
        workflow="partition",
    )

    registry.cancel_user_job("41")

    with pytest.raises(
        SolverJobCancelledError,
        match="cancelled before execution",
    ):
        registry.mark_running(
            token=job.token,
            user_id="41",
            celery_task_id="celery-123",
        )
