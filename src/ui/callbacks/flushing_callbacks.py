from __future__ import annotations

import logging
import math
import re

import dash_bootstrap_components as dbc
from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate

from src.services.flushing_runner import call_staci_flush_service
from src.services.model_storage import resolve_uploaded_model
from src.ui import ids
from src.ui.pages.components import render_active_model_summary
from src.ui.pages.flushing_analysis import render_flushing_results


logger = logging.getLogger(__name__)


def parse_hydrant_ids(value: str | None) -> list[str]:
    if not value:
        raise ValueError("Enter at least one hydrant junction ID.")

    node_ids = [
        part.strip()
        for part in re.split(r"[,;\r\n]+", value)
        if part.strip()
    ]

    if not node_ids:
        raise ValueError("Enter at least one hydrant junction ID.")

    if len(set(node_ids)) != len(node_ids):
        raise ValueError("Hydrant junction IDs must be unique.")

    return node_ids


def _positive_number(value, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a number.") from exc

    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{label} must be greater than zero.")

    return number


def _nonnegative_number(value, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a number.") from exc

    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} must be zero or greater.")

    return number


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
        Output(ids.FLUSH_RUN_STORE, "data"),
        Output(ids.FLUSH_RUN_STATUS, "children"),
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
    def run_flushing(
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

            area = _positive_number(
                hydrant_area,
                "Outlet area",
            )
            coefficient = _positive_number(
                loss_coefficient,
                "Total loss coefficient",
            )
            threshold = _nonnegative_number(
                velocity_threshold,
                "Velocity threshold",
            )
            pressure = _nonnegative_number(
                min_pressure_head,
                "Minimum pressure head",
            )

            inp_path = resolve_uploaded_model(
                network_state["model_id"],
                network_state["filename"],
            )

            logger.info(
                "Flushing plan started: "
                "model_id=%s mode=%s hydrants=%d",
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
                "Flushing plan finished: "
                "run_id=%s model_id=%s status=%s scenarios=%s",
                run_state.get("run_id", ""),
                run_state.get("model_id", ""),
                run_state.get("status", ""),
                run_state.get("scenario_count", ""),
            )

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

        color = (
            "warning"
            if run_state.get("partial")
            else "success"
        )
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

    @app.callback(
        Output(ids.FLUSH_RESULTS, "children"),
        Input(ids.FLUSH_RUN_STORE, "data"),
    )
    def render_results(run_state):
        return render_flushing_results(run_state)