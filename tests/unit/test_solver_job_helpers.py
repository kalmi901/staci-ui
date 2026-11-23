from __future__ import annotations

from unittest.mock import patch

import fakeredis
import pytest
from flask import Flask

from src.services.solver_jobs import (
    ActiveSolverJobError,
    SolverJobRegistry,
)
from src.ui.callbacks import solver_job_helpers


@pytest.fixture
def registry() -> SolverJobRegistry:
    return SolverJobRegistry(
        fakeredis.FakeRedis(
            decode_responses=True,
        ),
        ttl_seconds=3600,
        capacity=2,
        token_factory=lambda: "job-token",
        key_prefix="test:callback-solver",
    )


@pytest.fixture
def flask_app() -> Flask:
    return Flask(__name__)


def test_reserve_solver_job_uses_verified_user(
    registry: SolverJobRegistry,
    flask_app: Flask,
) -> None:
    with (
        patch.object(
            solver_job_helpers,
            "solver_job_registry",
            registry,
        ),
        flask_app.test_request_context(
            headers={
                "X-Staci-User-Id": "41",
                "X-Staci-User-Login": "alice",
            }
        ),
    ):
        request_state = solver_job_helpers.reserve_solver_job(
            workflow="hydraulic",
            payload={
                "model_id": "abcdef123456",
            },
        )

    assert request_state == {
        "token": "job-token",
        "workflow": "hydraulic",
        "payload": {
            "model_id": "abcdef123456",
        },
    }

    status = registry.status_for_user("41")

    assert status.user_job is not None
    assert status.user_job.state == "queued"
    assert status.queue_position == 1


def test_reserve_solver_job_rejects_second_user_job(
    registry: SolverJobRegistry,
    flask_app: Flask,
) -> None:
    with (
        patch.object(
            solver_job_helpers,
            "solver_job_registry",
            registry,
        ),
        flask_app.test_request_context(
            headers={
                "X-Staci-User-Id": "41",
                "X-Staci-User-Login": "alice",
            }
        ),
    ):
        solver_job_helpers.reserve_solver_job(
            workflow="hydraulic",
            payload={},
        )

        with pytest.raises(
            ActiveSolverJobError,
            match="queued hydraulic",
        ):
            solver_job_helpers.reserve_solver_job(
                workflow="partition",
                payload={},
            )


def test_running_solver_job_completes_and_releases_slot(
    registry: SolverJobRegistry,
    flask_app: Flask,
) -> None:
    with (
        patch.object(
            solver_job_helpers,
            "solver_job_registry",
            registry,
        ),
        flask_app.test_request_context(
            headers={
                "X-Staci-User-Id": "41",
                "X-Staci-User-Login": "alice",
            }
        ),
    ):
        request_state = solver_job_helpers.reserve_solver_job(
            workflow="hydraulic",
            payload={"value": 7},
        )

        with solver_job_helpers.running_solver_job(
            request_state,
            workflow="hydraulic",
        ) as (execution, payload):
            assert payload == {"value": 7}
            assert registry.status_for_user("41").user_job.state == "running"  # pyright: ignore[reportOptionalMemberAccess]

            execution.complete()

    status = registry.status_for_user("41")

    assert status.running_jobs == 0
    assert status.queued_jobs == 0
    assert status.user_job is None


def test_running_solver_job_defaults_to_failed(
    registry: SolverJobRegistry,
    flask_app: Flask,
) -> None:
    with (
        patch.object(
            solver_job_helpers,
            "solver_job_registry",
            registry,
        ),
        flask_app.test_request_context(
            headers={
                "X-Staci-User-Id": "41",
                "X-Staci-User-Login": "alice",
            }
        ),
    ):
        request_state = solver_job_helpers.reserve_solver_job(
            workflow="flushing",
            payload={},
        )

        with solver_job_helpers.running_solver_job(
            request_state,
            workflow="flushing",
        ):
            pass

    finished = registry.get_job("job-token")

    assert finished is not None
    assert finished.state == "failed"
    assert registry.status_for_user("41").user_job is None


def test_solver_job_requires_identity(
    registry: SolverJobRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "STACI_UI_DEV_USER_ID",
        raising=False,
    )
    monkeypatch.delenv(
        "STACI_UI_DEV_USER_LOGIN",
        raising=False,
    )

    with (
        patch.object(
            solver_job_helpers,
            "solver_job_registry",
            registry,
        ),
        pytest.raises(
            PermissionError,
            match="Authentication is required",
        ),
    ):
        solver_job_helpers.reserve_solver_job(
            workflow="hydraulic",
            payload={},
        )
