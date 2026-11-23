from __future__ import annotations

import logging
import re

import dash_bootstrap_components as dbc
from dash import Input, Output, State, html, no_update
from dash.exceptions import PreventUpdate

from src.run_logging import logged_run
from src.services.flushing_runner import (
    call_staci_flush_service,
    load_flushing_scenario,
)
from src.services.model_storage import resolve_uploaded_model
from src.services.solver_jobs import ActiveSolverJobError, SolverJobCancelledError
from src.ui import ids
from src.ui.callbacks.helpers import nonnegative_number, positive_number
from src.ui.callbacks.solver_job_helpers import reserve_solver_job, running_solver_job
from src.ui.pages.components import render_active_model_summary
from src.ui.pages.flushing_analysis import render_flushing_results
from src.visualisation.common import make_empty_network_figure
from src.visualisation.flushing import make_flushing_scenario_figure

logger = logging.getLogger(__name__)


@logged_run("flushing")
def _execute_flushing(
    n_clicks,
    network_state,
    hydrant_text,
    mode,
    hydrant_area,
    loss_coefficient,
    velocity_threshold,
    min_pressure_head,
    write_networks,
):
    if not n_clicks:
        raise PreventUpdate

    if not network_state:
        return None, dbc.Alert(
            "No active INP file. Upload a model first.",
            color="warning",
            className="upload-alert",
        )

    try:
        hydrant_ids = parse_hydrant_ids(hydrant_text)

        if mode not in {"single", "multi"}:
            raise ValueError("Select a valid flushing mode.")

        area = positive_number(hydrant_area, "Outlet area")
        coefficient = positive_number(loss_coefficient, "Total loss coefficient")
        threshold = nonnegative_number(velocity_threshold, "Velocity threshold")
        pressure = nonnegative_number(min_pressure_head, "Minimum pressure head")

        inp_path = resolve_uploaded_model(
            network_state["model_id"],
            network_state["filename"],
        )

        logger.info(
            "Flushing plan started: model_id=%s mode=%s hydrants=%d",
            network_state.get("model_id", ""),
            mode,
            len(hydrant_ids),
        )

        run_state = call_staci_flush_service(
            inp_path,
            model_id=network_state["model_id"],
            hydrant_node_ids=hydrant_ids,
            hydrant_area_m2=area,
            total_loss_coefficient=coefficient,
            velocity_threshold_mps=threshold,
            mode=mode,
            min_pressure_head_m=pressure,
            write_network_files=bool(write_networks),
        )

        logger.info(
            "Flushing plan finished: run_id=%s model_id=%s status=%s scenarios=%s",
            run_state.get("run_id", ""),
            run_state.get("model_id", ""),
            run_state.get("status", ""),
            run_state.get("scenario_count", ""),
        )

    except SolverJobCancelledError:
        raise

    except Exception as exc:
        logger.exception(
            "Flushing plan failed: model_id=%s",
            network_state.get("model_id", ""),
        )
        return None, dbc.Alert(
            f"Flushing plan failed: {exc}",
            color="danger",
            className="upload-alert",
        )

    color = "warning" if run_state.get("partial") else "success"
    message = (
        "Flushing plan completed with partial results."
        if run_state.get("partial")
        else "Flushing plan completed successfully."
    )

    return run_state, dbc.Alert(
        children=[
            html.Div(
                message,
                style={"fontWeight": 800},
            ),
            html.Div(
                f"Run ID: {run_state['run_id']} · "
                f"Scenarios: {run_state['scenario_count']} · "
                f"Plan steps: {run_state['plan_count']}"
            ),
        ],
        color=color,
        className="upload-alert",
    )


def parse_hydrant_ids(value: str | None) -> list[str]:
    if not value:
        raise ValueError("Enter at least one hydrant junction ID.")

    node_ids = [part.strip() for part in re.split(r"[,;\r\n]+", value) if part.strip()]

    if not node_ids:
        raise ValueError("Enter at least one hydrant junction ID.")

    if len(set(node_ids)) != len(node_ids):
        raise ValueError("Hydrant junction IDs must be unique.")

    return node_ids


def register_flushing_callbacks(app):
    @app.callback(
        Output(ids.FLUSH_ACTIVE_MODEL_SUMMARY, "children"),
        Output(ids.FLUSH_RUN_BUTTON, "disabled"),
        Input(ids.NETWORK_STORE, "data"),
    )
    def sync_active_model(network_state):
        return (
            render_active_model_summary(network_state),
            not bool(network_state),
        )

    @app.callback(
        Output(ids.FLUSH_JOB_REQUEST_STORE, "data"),
        Output(ids.FLUSH_RUN_STATUS, "children", allow_duplicate=True),
        Input(ids.FLUSH_RUN_BUTTON, "n_clicks"),
        State(ids.NETWORK_STORE, "data"),
        State(ids.FLUSH_HYDRANT_IDS, "value"),
        State(ids.FLUSH_MODE, "value"),
        State(ids.FLUSH_HYDRANT_AREA, "value"),
        State(ids.FLUSH_LOSS_COEFFICIENT, "value"),
        State(ids.FLUSH_VELOCITY_THRESHOLD, "value"),
        State(ids.FLUSH_MIN_PRESSURE_HEAD, "value"),
        State(ids.FLUSH_WRITE_NETWORKS, "value"),
        prevent_initial_call=True,
    )
    def submit_flushing(
        n_clicks,
        network_state,
        hydrant_text,
        mode,
        hydrant_area,
        loss_coefficient,
        velocity_threshold,
        min_pressure_head,
        write_networks,
    ):
        if not n_clicks:
            raise PreventUpdate

        if not network_state:
            return no_update, dbc.Alert(
                "No active INP file. Upload a model first.",
                color="warning",
                className="upload-alert",
            )

        try:
            request_state = reserve_solver_job(
                workflow="flushing",
                payload={
                    "network_state": network_state,
                    "hydrant_text": hydrant_text,
                    "mode": mode,
                    "hydrant_area": hydrant_area,
                    "loss_coefficient": loss_coefficient,
                    "velocity_threshold": velocity_threshold,
                    "min_pressure_head": min_pressure_head,
                    "write_networks": write_networks,
                },
            )

        except ActiveSolverJobError as exc:
            logger.info(
                "Flushing submission rejected: %s",
                exc,
            )

            return no_update, dbc.Alert(
                str(exc),
                color="warning",
                className="upload-alert",
            )

        except Exception as exc:
            logger.exception("Flushing submission failed.")

            return no_update, dbc.Alert(
                f"Flushing submission failed: {exc}",
                color="danger",
                className="upload-alert",
            )

        return request_state, dbc.Alert(
            "Flushing analysis was added to the solver queue.",
            color="info",
            className="upload-alert",
        )

    @app.callback(
        Output(ids.FLUSH_RUN_STORE, "data"),
        Output(ids.FLUSH_RUN_STATUS, "children"),
        Input(ids.FLUSH_JOB_REQUEST_STORE, "data"),
        background=True,
        running=[
            (
                Output(ids.FLUSH_RUN_BUTTON, "disabled"),
                True,
                False,
            ),
        ],
        prevent_initial_call=True,
    )
    def run_flushing(request_state):
        if not request_state:
            raise PreventUpdate

        try:
            with running_solver_job(
                request_state,
                workflow="flushing",
            ) as (execution, payload):
                result = _execute_flushing(
                    1,
                    payload.get("network_state"),
                    payload.get("hydrant_text"),
                    payload.get("mode"),
                    payload.get("hydrant_area"),
                    payload.get("loss_coefficient"),
                    payload.get("velocity_threshold"),
                    payload.get("min_pressure_head"),
                    payload.get("write_networks"),
                )

                run_state = (
                    result[0] if isinstance(result, (tuple, list)) and result else None
                )

                # A partial flushing result is still a completed
                # solver job, not a failed job.
                if isinstance(run_state, dict):
                    execution.complete()

                return result

        except SolverJobCancelledError:
            logger.info("Flushing analysis was cancelled.")

            return None, dbc.Alert(
                "Flushing analysis was cancelled.",
                color="secondary",
                className="upload-alert",
            )

        except Exception as exc:
            logger.exception("Flushing background job failed.")

            return None, dbc.Alert(
                f"Flushing analysis failed: {exc}",
                color="danger",
                className="upload-alert",
            )

    @app.callback(
        Output(ids.FLUSH_RESULTS, "children"),
        Input(ids.FLUSH_RUN_STORE, "data"),
    )
    def render_results(run_state):
        return render_flushing_results(run_state)

    @app.callback(
        Output(ids.FLUSH_NETWORK_GRAPH, "figure"),
        Input(ids.FLUSH_SCENARIO, "value"),
        Input(ids.FLUSH_MAP_MODE, "value"),
        Input(ids.FLUSH_LINE_WIDTH, "value"),
        Input(ids.FLUSH_MARKER_SIZE, "value"),
        Input(ids.FLUSH_HIDE_NODES, "value"),
        State(ids.FLUSH_RUN_STORE, "data"),
        State(ids.NETWORK_VIEW_STORE, "data"),
    )
    def render_scenario_map(
        scenario_id,
        map_mode,
        line_width_scale,
        marker_size,
        hide_nodes,
        run_state,
        network_view_state,
    ):
        if not run_state or not scenario_id:
            return make_empty_network_figure(
                "Run STACI Flush and select a scenario.",
                icon="🚿",
                title="No flushing scenario selected",
            )

        try:
            scenario_state = load_flushing_scenario(
                run_state["run_id"],
                scenario_id,
            )

        except Exception as exc:
            logger.exception(
                "Flushing scenario load failed: run_id=%s scenario_id=%s",
                run_state.get("run_id", ""),
                scenario_id,
            )

            return make_empty_network_figure(
                f"Could not load flushing scenario: {exc}",
                tone="danger",
            )

        candidate_ids = (
            [
                str(row["node_id"])
                for row in run_state.get("plan", [])
                if row.get("node_id")
            ]
            if run_state.get("mode") == "single"
            else []
        )

        return make_flushing_scenario_figure(
            network_view_state,
            scenario_state,
            map_mode=map_mode,
            candidate_hydrant_ids=candidate_ids,
            line_width_scale=line_width_scale,
            marker_size=marker_size,
            hide_nodes=hide_nodes,
        )
