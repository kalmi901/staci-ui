from __future__ import annotations

import logging

from dash import Input, Output, html

from src.background_jobs import solver_job_registry
from src.services.solver_jobs import SolverQueueStatus
from src.ui import ids
from src.user_identity import current_user_identity

logger = logging.getLogger(__name__)

_WORKFLOW_LABELS = {
    "hydraulic": "hydraulic simulation",
    "partition": "network partitioning",
    "flushing": "flushing plan",
    "calibration": "pipe calibration",
}


def render_solver_status(
    status: SolverQueueStatus,
):
    busy = status.running_jobs >= status.capacity or status.queued_jobs > 0

    availability = "Busy" if busy else "Available"
    badge_class = (
        "solver-status-badge solver-status-badge-busy"
        if busy
        else "solver-status-badge solver-status-badge-available"
    )

    if status.user_job is None:
        user_message = "You have no active solver job."
    else:
        workflow = _WORKFLOW_LABELS.get(
            status.user_job.workflow,
            status.user_job.workflow,
        )

        if status.user_job.state == "queued":
            user_message = f"Your {workflow} job is waiting."

            if status.queue_position is not None:
                user_message += f" Queue position: {status.queue_position}."
        else:
            user_message = f"Your {workflow} job is {status.user_job.state}."

    return html.Div(
        className="solver-status-content",
        children=[
            html.Div(
                className="solver-status-header",
                children=[
                    html.Span(
                        "Solver status",
                        className="solver-status-title",
                    ),
                    html.Span(
                        availability,
                        className=badge_class,
                    ),
                ],
            ),
            html.Div(
                (
                    f"{status.running_jobs}/{status.capacity} "
                    "solver slots active"
                    f" · {status.queued_jobs} waiting"
                ),
                className="solver-status-summary",
            ),
            html.Div(
                user_message,
                className="solver-status-message",
            ),
        ],
    )


def load_solver_status():
    identity = current_user_identity()

    if identity is None:
        return html.Div(
            "Solver status is unavailable.",
            className="solver-status-message",
        )

    try:
        status = solver_job_registry.status_for_user(identity.user_id)
    except Exception:
        # Polling happens frequently, therefore avoid flooding production logs.
        logger.debug(
            "Could not read solver queue status.",
            exc_info=True,
        )
        return html.Div(
            "Solver status is temporarily unavailable.",
            className="solver-status-message",
        )

    return render_solver_status(status)


def register_solver_status_callbacks(app):
    @app.callback(
        Output(ids.SOLVER_STATUS, "children"),
        Input(ids.SOLVER_STATUS_INTERVAL, "n_intervals"),
    )
    def update_solver_status(_n_intervals):
        return load_solver_status()
