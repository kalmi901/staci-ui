from __future__ import annotations

import logging

import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate

from src.run_logging import logged_run
from src.services.hydraulic_runner import call_hydraulic_simulator
from src.services.inp_model_reader import read_model_options
from src.services.model_storage import resolve_uploaded_model
from src.services.solver_jobs import ActiveSolverJobError, SolverJobCancelledError
from src.ui import ids
from src.ui.callbacks.helpers import resolve_color_range_outputs
from src.ui.callbacks.solver_job_helpers import (
    require_user_identity,
    reserve_solver_job,
    running_solver_job,
)
from src.ui.pages.components import render_active_model_summary
from src.ui.pages.hydraulic_analysis import render_success_alert
from src.visualisation.network_preview import make_hydraulic_timestep_figure

logger = logging.getLogger(__name__)

PLAY_STR = "▶ Play"
PAUSE_STR = "⏸ Pause"


@logged_run("hydraulic")
def _execute_hydraulic_simulation(
    n_clicks,
    network_state,
    backend,
    override_enabled,
    duration,
    hydraulic_timestep,
    report_timestep,
    rule_timestep,
    demand_multiplier,
):
    if not n_clicks:
        raise PreventUpdate

    if not network_state:
        return None, dbc.Alert(
            "No active INP file. Upload a model first.",
            color="warning",
            className="upload-alert",
        )  # pyright: ignore[reportCallIssue]

    try:
        identity = require_user_identity()

        inp_path = resolve_uploaded_model(
            network_state["model_id"],
            network_state["filename"],
            user_id=identity.user_id,
        )

        option_overrides = None
        if override_enabled:
            required_values = {
                "duration": duration,
                "hydraulic timestep": hydraulic_timestep,
                "report timestep": report_timestep,
                "rule timestep": rule_timestep,
                "demand multiplier": demand_multiplier,
            }

            missing = [name for name, value in required_values.items() if value is None]

            if missing:
                raise ValueError(
                    "Missing hydraulic override values: " + ", ".join(missing) + "."
                )

            if duration < 0:
                raise ValueError("Duration must be non-negative.")
            for name, value in (
                ("Hydraulic timestep", hydraulic_timestep),
                ("Report timestep", report_timestep),
                ("Rule timestep", rule_timestep),
            ):
                if value <= 0:
                    raise ValueError(f"{name} must be greater than zero.")

            if demand_multiplier < 0:
                raise ValueError("Demand multiplier must be non-negative.")

            option_overrides = {
                "duration": duration * 3600,
                "hydraulic_timestep": hydraulic_timestep * 60,
                "report_timestep": report_timestep * 60,
                "rule_timestep": rule_timestep * 60,
                "demand_multiplier": demand_multiplier,
            }

        logger.info(
            "Hydraulic simulation started: model_id=%s, backend=%s",
            network_state.get("model_id"),
            backend,
        )

        run_state = call_hydraulic_simulator(
            inp_path,
            model_id=network_state.get("model_id", ""),
            user_id=identity.user_id,
            backend=backend,
            option_overrides=option_overrides,
        )

        logger.info(
            "Hydraulic simulation finished: model_id=%s, run_id=%s, backend=%s",
            run_state.get("model_id", ""),
            run_state.get("run_id", ""),
            run_state.get("backend", ""),
        )

    except SolverJobCancelledError:
        raise

    except Exception as exc:
        logger.exception(
            "Hydraulic simulation failed: model_id=%s",
            network_state.get("model_id", ""),
        )
        return None, dbc.Alert(
            f"Hydraulic simulation failed: {exc}",
            color="danger",
            className="upload-alert",
        )  # pyright: ignore[reportCallIssue]

    return run_state, render_success_alert(run_state)


def register_hydraulic_callbacks(app):

    @app.callback(
        Output(ids.HYD_ACTIVE_MODEL_SUMMARY, "children"),
        Output(ids.HYD_RUN_BUTTON, "disabled"),
        Input(ids.NETWORK_STORE, "data"),
    )
    def sync_hydraulic_active_model(network_state):
        if not network_state:
            return render_active_model_summary(network_state), True

        return render_active_model_summary(network_state), False

    @app.callback(
        Output(ids.HYD_DURATION_HOURS, "disabled"),
        Output(ids.HYD_TIMESTEP_MINUTES, "disabled"),
        Output(ids.HYD_REPORT_TIMESTEP_MINUTES, "disabled"),
        Output(ids.HYD_RULE_TIMESTEP_MINUTES, "disabled"),
        Output(ids.HYD_DEMAND_MULTIPLIER, "disabled"),
        Input(ids.HYD_OVERRIDE_OPTIONS, "value"),
    )
    def toggle_hydraulic_overrides(enabled):
        disabled = not bool(enabled)
        return disabled, disabled, disabled, disabled, disabled

    @app.callback(
        Output(ids.HYD_DURATION_HOURS, "value"),
        Output(ids.HYD_TIMESTEP_MINUTES, "value"),
        Output(ids.HYD_REPORT_TIMESTEP_MINUTES, "value"),
        Output(ids.HYD_RULE_TIMESTEP_MINUTES, "value"),
        Output(ids.HYD_DEMAND_MULTIPLIER, "value"),
        Input(ids.NETWORK_STORE, "data"),
    )
    def render_simulation_options(network_state):
        if not network_state:
            return None, None, None, None, None

        try:
            identity = require_user_identity()
            inp_path = resolve_uploaded_model(
                network_state["model_id"],
                network_state["filename"],
                user_id=identity.user_id,
            )
            options = read_model_options(inp_path)

            return (
                options["duration"] / 3600,  # seconds --> hours
                options["hydraulic_timestep"] / 60,  # seconds --> minutes
                options["report_timestep"] / 60,  # seconds --> minutes
                options["rule_timestep"] / 60,  # seconds --> minutes
                options["demand_multiplier"],
            )

        except Exception:
            logger.exception(
                "Failed to read hydraulic options: model_id=%s",
                network_state.get("model_id", ""),
            )
            return None, None, None, None, None

    @app.callback(
        Output(ids.HYD_JOB_REQUEST_STORE, "data"),
        Output(ids.HYD_RUN_STATUS, "children", allow_duplicate=True),
        Input(ids.HYD_RUN_BUTTON, "n_clicks"),
        State(ids.NETWORK_STORE, "data"),
        State(ids.HYD_BACKEND, "value"),
        State(ids.HYD_OVERRIDE_OPTIONS, "value"),
        State(ids.HYD_DURATION_HOURS, "value"),
        State(ids.HYD_TIMESTEP_MINUTES, "value"),
        State(ids.HYD_REPORT_TIMESTEP_MINUTES, "value"),
        State(ids.HYD_RULE_TIMESTEP_MINUTES, "value"),
        State(ids.HYD_DEMAND_MULTIPLIER, "value"),
        prevent_initial_call=True,
    )
    def submit_hydraulic_simulation(
        n_clicks,
        network_state,
        backend,
        override_enabled,
        duration,
        hydraulic_timestep,
        report_timestep,
        rule_timestep,
        demand_multiplier,
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
                workflow="hydraulic",
                payload={
                    "network_state": network_state,
                    "backend": backend,
                    "override_enabled": override_enabled,
                    "duration": duration,
                    "hydraulic_timestep": hydraulic_timestep,
                    "report_timestep": report_timestep,
                    "rule_timestep": rule_timestep,
                    "demand_multiplier": demand_multiplier,
                },
            )

        except ActiveSolverJobError as exc:
            logger.info(
                "Hydraulic submission rejected: %s",
                exc,
            )

            return no_update, dbc.Alert(
                str(exc),
                color="warning",
                className="upload-alert",
            )

        except Exception as exc:
            logger.exception("Hydraulic submission failed.")

            return no_update, dbc.Alert(
                f"Hydraulic submission failed: {exc}",
                color="danger",
                className="upload-alert",
            )

        return request_state, dbc.Alert(
            "Hydraulic simulation was added to the solver queue.",
            color="info",
            className="upload-alert",
        )

    @app.callback(
        Output(ids.HYD_RUN_STORE, "data"),
        Output(ids.HYD_RUN_STATUS, "children"),
        Input(ids.HYD_JOB_REQUEST_STORE, "data"),
        background=True,
        running=[
            (
                Output(ids.HYD_RUN_BUTTON, "disabled"),
                True,
                False,
            ),
        ],
        prevent_initial_call=True,
    )
    def run_hydraulic_simulation(request_state):
        if not request_state:
            raise PreventUpdate

        try:
            with running_solver_job(
                request_state,
                workflow="hydraulic",
            ) as (execution, payload):
                result = _execute_hydraulic_simulation(
                    1,
                    payload.get("network_state"),
                    payload.get("backend"),
                    payload.get("override_enabled"),
                    payload.get("duration"),
                    payload.get("hydraulic_timestep"),
                    payload.get("report_timestep"),
                    payload.get("rule_timestep"),
                    payload.get("demand_multiplier"),
                )

                run_state = (
                    result[0] if isinstance(result, (tuple, list)) and result else None
                )

                if isinstance(run_state, dict):
                    execution.complete()

                return result

        except SolverJobCancelledError:
            logger.info("Hydraulic simulation was cancelled.")

            return None, dbc.Alert(
                "Hydraulic simulation was cancelled.",
                color="secondary",
                className="upload-alert",
            )

        except Exception as exc:
            logger.exception("Hydraulic background job failed.")

            return None, dbc.Alert(
                f"Hydraulic simulation failed: {exc}",
                color="danger",
                className="upload-alert",
            )

    # -- Animation --
    @app.callback(
        Output(ids.HYD_TIME_SLIDER, "min"),
        Output(ids.HYD_TIME_SLIDER, "max"),
        Output(ids.HYD_TIME_SLIDER, "marks"),
        Output(ids.HYD_TIME_SLIDER, "value"),
        Output(ids.HYD_TIME_SLIDER, "disabled"),
        Output(ids.HYD_ANIMATION_INTERVAL, "disabled"),
        Output(ids.HYD_PLAY_BUTTON, "children"),
        Output(ids.HYD_PLAY_BUTTON, "disabled"),
        Input(ids.URL, "pathname"),
        Input(ids.HYD_RUN_STORE, "data"),
        Input(ids.HYD_PLAY_BUTTON, "n_clicks"),
        Input(ids.HYD_ANIMATION_INTERVAL, "n_intervals"),
        State(ids.HYD_TIME_SLIDER, "value"),
        State(ids.HYD_ANIMATION_INTERVAL, "disabled"),
    )
    def control_hydraulic_time(
        pathname, run_state, play_clicks, n_intervals, current_value, interval_disabled
    ):

        # Enable / Disable Control
        if not run_state or run_state.get("status") != "success":
            return 0, 0, {0: "0"}, 0, True, True, PLAY_STR, True

        time = run_state.get("time", [])
        if not time:
            return 0, 0, {0: "0"}, 0, True, True, PLAY_STR, True

        max_index = len(time) - 1
        if max_index <= 0:
            return 0, 0, {0: "0"}, 0, True, True, PLAY_STR, True

        # Mark settings
        mark_indices = sorted(
            set(
                [
                    0,
                    max_index,
                    max_index // 4,
                    max_index // 2,
                    (3 * max_index) // 4,
                ]
            )
        )

        marks = {i: f"{int(time[i] / 3600)} h" for i in mark_indices}

        # -- Handle Inputs --
        # 1) Store Available
        if ctx.triggered_id == ids.HYD_RUN_STORE:
            return 0, max_index, marks, 0, False, True, PLAY_STR, False

        # 2) PLAY/PAUSE Button pressed
        if ctx.triggered_id == ids.HYD_PLAY_BUTTON:
            should_start = bool(interval_disabled)

            if should_start:
                return (
                    0,
                    max_index,
                    marks,
                    current_value or 0,
                    False,
                    False,
                    PAUSE_STR,
                    False,
                )

            return 0, max_index, marks, current_value or 0, False, True, PLAY_STR, False

        # 3) Increse time value
        if ctx.triggered_id == ids.HYD_ANIMATION_INTERVAL:
            value = current_value or 0
            value = (value + 1) % (max_index + 1)

            return 0, max_index, marks, value, False, False, PAUSE_STR, False

        return 0, max_index, marks, current_value or 0, False, True, PLAY_STR, False

    @app.callback(
        Output(ids.HYD_NODE_COLOR_MIN, "value"),
        Output(ids.HYD_NODE_COLOR_MAX, "value"),
        Output(ids.HYD_NODE_COLOR_MIN, "disabled"),
        Output(ids.HYD_NODE_COLOR_MAX, "disabled"),
        Output(ids.HYD_LINK_COLOR_MIN, "value"),
        Output(ids.HYD_LINK_COLOR_MAX, "value"),
        Output(ids.HYD_LINK_COLOR_MIN, "disabled"),
        Output(ids.HYD_LINK_COLOR_MAX, "disabled"),
        Input(ids.HYD_RUN_STORE, "data"),
        Input(ids.HYD_NODE_RESULT, "value"),
        Input(ids.HYD_LINK_RESULT, "value"),
        prevent_initial_call=True,
    )
    def sync_hydraulic_color_range(run_state, node_result, link_result):
        if not run_state or run_state.get("status") != "success":
            return (
                None,
                None,
                True,
                True,
                None,
                None,
                True,
                True,
            )

        ranges = run_state.get("ranges", {})
        node_values = resolve_color_range_outputs(ranges, node_result)
        link_values = resolve_color_range_outputs(ranges, link_result)

        if ctx.triggered_id == ids.HYD_NODE_RESULT:
            return *node_values, no_update, no_update, no_update, no_update

        if ctx.triggered_id == ids.HYD_LINK_RESULT:
            return no_update, no_update, no_update, no_update, *link_values

        return *node_values, *link_values

    @app.callback(
        Output(ids.HYD_NETWORK_GRAPH, "figure"),
        Input(ids.HYD_RUN_STORE, "data"),
        Input(ids.HYD_TIME_SLIDER, "value"),
        Input(ids.HYD_NODE_RESULT, "value"),
        Input(ids.HYD_LINK_RESULT, "value"),
        Input(ids.HYD_NODE_COLOR_MIN, "value"),
        Input(ids.HYD_NODE_COLOR_MAX, "value"),
        Input(ids.HYD_LINK_COLOR_MIN, "value"),
        Input(ids.HYD_LINK_COLOR_MAX, "value"),
        State(ids.NETWORK_VIEW_STORE, "data"),
        Input(ids.HYD_LINE_WIDTH, "value"),
        Input(ids.HYD_MARKER_SIZE, "value"),
        Input(ids.HYD_HIDE_NODES, "value"),
    )
    def render_hydraulic_network_graph(
        run_state,
        time_index,
        node_result,
        link_result,
        node_cmin,
        node_cmax,
        link_cmin,
        link_cmax,
        network_view_state,
        line_width_scale,
        marker_size,
        hide_nodes,
    ):
        identity = require_user_identity()

        return make_hydraulic_timestep_figure(
            network_view_state=network_view_state,
            run_state=run_state,
            user_id=identity.user_id,
            time_index=time_index,
            node_result=node_result,
            link_result=link_result,
            node_cmin=node_cmin,
            node_cmax=node_cmax,
            link_cmin=link_cmin,
            link_cmax=link_cmax,
            line_width_scale=line_width_scale,
            marker_size=marker_size,
            hide_nodes=hide_nodes,
        )
