from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from celery import current_task

from src.background_jobs import solver_job_registry
from src.services.solver_jobs import (
    SolverJob,
    SolverJobCancelledError,
    SolverWorkflow,
    TerminalJobState,
    solver_cancellation_scope,
)
from src.user_identity import (
    UserIdentity,
    current_user_identity,
)


@dataclass
class SolverJobExecution:
    token: str
    user_id: str
    state: TerminalJobState = "failed"

    def complete(self) -> None:
        self.state = "completed"

    def cancel(self) -> None:
        self.state = "cancelled"


def require_user_identity() -> UserIdentity:
    identity = current_user_identity()

    if identity is None:
        raise PermissionError("Authentication is required.")

    return identity


def reserve_solver_job(
    *,
    workflow: SolverWorkflow,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Reserve the user's solver slot before Celery submission."""

    identity = require_user_identity()

    job = solver_job_registry.submit(
        user_id=identity.user_id,
        workflow=workflow,
    )

    return {
        "token": job.token,
        "workflow": job.workflow,
        "payload": dict(payload),
    }


def cancel_current_user_solver_job() -> SolverJob | None:
    identity = require_user_identity()

    return solver_job_registry.cancel_user_job(identity.user_id)


def _parse_job_request(
    request_state: Mapping[str, Any] | None,
    *,
    workflow: SolverWorkflow,
) -> tuple[str, dict[str, Any]]:
    if not isinstance(request_state, Mapping):
        raise ValueError("Solver job request is missing.")

    token = request_state.get("token")
    request_workflow = request_state.get("workflow")
    payload = request_state.get("payload")

    if not isinstance(token, str) or not token:
        raise ValueError("Solver job token is missing.")

    if request_workflow != workflow:
        raise ValueError("Solver job workflow does not match the callback.")

    if not isinstance(payload, Mapping):
        raise ValueError("Solver job payload is missing.")

    return token, dict(payload)


def _current_celery_task_id() -> str | None:
    if current_task is None:
        return None

    request = getattr(
        current_task,
        "request",
        None,
    )
    task_id = getattr(
        request,
        "id",
        None,
    )

    return str(task_id) if task_id else None


@contextmanager
def running_solver_job(
    request_state: Mapping[str, Any] | None,
    *,
    workflow: SolverWorkflow,
) -> Iterator[
    tuple[
        SolverJobExecution,
        dict[str, Any],
    ]
]:
    """Move a reserved job to running and always release its user slot."""

    identity = require_user_identity()

    token, payload = _parse_job_request(
        request_state,
        workflow=workflow,
    )

    solver_job_registry.mark_running(
        token=token,
        user_id=identity.user_id,
        celery_task_id=_current_celery_task_id(),
    )

    execution = SolverJobExecution(
        token=token,
        user_id=identity.user_id,
    )

    def cancellation_requested() -> bool:
        return solver_job_registry.cancellation_requested(
            token=execution.token,
            user_id=execution.user_id,
        )

    with solver_cancellation_scope(cancellation_requested):
        try:
            yield execution, payload

            if cancellation_requested():
                execution.cancel()
                raise SolverJobCancelledError("Solver job was cancelled.")

        except SolverJobCancelledError:
            execution.cancel()
            raise

        finally:
            solver_job_registry.finish(
                token=execution.token,
                user_id=execution.user_id,
                state=execution.state,
            )
