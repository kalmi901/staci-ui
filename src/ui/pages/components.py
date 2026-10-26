# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations

from typing import Any

from dash import dcc, html
import dash_bootstrap_components as dbc


_COLOR_RANGE_DIGITS = {
    "elevation": 2,
    "length": 2,
    "roughness": 2,
    "head": 2,
    "pressure": 2,
    "diameter": 4,
    "velocity": 4,
    "headloss": 4,
    "demand": 6,
    "flowrate": 6,
}


def round_color_range_value(
    attribute: str | None,
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    digits = _COLOR_RANGE_DIGITS.get(
        str(attribute),
        4,
    )

    return round(number, digits)



def create_page_header(
    title: str,
    subtitle: str,
    badge: str,
):
    return html.Div(
        className="page-header",
        children=[
            html.Div(
                children=[
                    html.H1(title),
                    html.P(subtitle),
                ],
            ),
            dbc.Badge(
                badge,
                color="info",
                className="page-badge",
            ),
        ],
    )


def render_empty_model_summary(message: str):
    return html.Div(
        className="model-summary-empty",
        children=[
            html.Div(
                "No active model",
                className="model-summary-title",
            ),
            html.P(message),
        ],
    )


def create_metric_item(
    label: str,
    value: Any,
):
    return html.Div(
        className="meta-item",
        children=[
            html.Div(label, className="meta-label"),
            html.Div(str(value), className="meta-value"),
        ],
    )


def render_active_model_summary(
    network_state: dict[str, Any] | None,
):
    if not network_state:
        return render_empty_model_summary(
            "Go to Load Model and upload an EPANET .inp file first."
        )

    summary = network_state.get("summary", {})
    nodes = summary.get("Nodes", {})
    links = summary.get("Links", {})

    return html.Div(
        className="model-summary",
        children=[
            html.Div(
                className="model-summary-header",
                children=[
                    html.Div(
                        children=[
                            html.Div(
                                network_state.get("filename", "—"),
                                className="model-summary-title",
                            ),
                            html.Div(
                                f"Model ID: "
                                f"{network_state.get('model_id', '—')}",
                                className="small-status",
                            ),
                        ],
                    ),
                    dbc.Badge(
                        "Model Ready",
                        color="success",
                    ),
                ],
            ),
            html.Div(
                className="model-storage-note",
                children=[
                    html.Div(
                        f"Junctions: "
                        f"{nodes.get('Junctions', '—')} · "
                        f"Tanks: {nodes.get('Tanks', '—')} · "
                        f"Reservoirs: "
                        f"{nodes.get('Reservoirs', '—')}"
                    ),
                    html.Div(
                        f"Pipes: {links.get('Pipes', '—')} · "
                        f"Pumps: {links.get('Pumps', '—')} · "
                        f"Valves: {links.get('Valves', '—')}"
                    ),
                ],
            ),
        ],
    )


def create_active_model_section(
    summary_id: str,
    *,
    title: str = "Model summary",
):
    return html.Div(
        className="setup-section",
        children=[
            html.H3(title),
            html.Div(
                id=summary_id,
                className="active-model-box",
                children=render_active_model_summary(None),
            ),
        ],
    )


def create_color_range_control(
    label: str,
    minimum_id: str,
    maximum_id: str,
    *,
    placeholder_prefix: str,
):
    return html.Div(
        className="plot-control color-range-inputs",
        children=[
            dbc.Label(label),
            html.Div(
                className="color-range-row",
                children=[
                    dbc.Input(
                        id=minimum_id,
                        type="number",
                        step="any",
                        placeholder=f"{placeholder_prefix}-min",
                        persistence=True,
                        persistence_type="memory",
                    ),
                    dbc.Input(
                        id=maximum_id,
                        type="number",
                        step="any",
                        placeholder=f"{placeholder_prefix}-max",
                        persistence=True,
                        persistence_type="memory",
                    ),
                ],
            ),
        ],
    )


def create_network_display_controls(
    line_width_id: str,
    marker_size_id: str,
    hide_nodes_id: str,
    *,
    default_marker_size: float = 5,
):
    return html.Div(
        className="network-display-controls",
        children=[
            html.Div(
                className="plot-control",
                children=[
                    dbc.Label("Line width scale"),
                    dbc.Input(
                        id=line_width_id,
                        type="number",
                        value=1.0,
                        min=0.25,
                        max=4.0,
                        step=0.25,
                        persistence=True,
                        persistence_type="memory",
                    ),
                ],
            ),
            html.Div(
                className="plot-control",
                children=[
                    dbc.Label("Marker size"),
                    dbc.Input(
                        id=marker_size_id,
                        type="number",
                        value=default_marker_size,
                        min=1,
                        max=20,
                        step=1,
                        persistence=True,
                        persistence_type="memory",
                    ),
                ],
            ),
            html.Div(
                className=(
                    "plot-control network-display-toggle"
                ),
                children=[
                    dbc.Label("Network nodes"),
                    dbc.Switch(
                        id=hide_nodes_id,
                        label="Hide nodes",
                        value=False,
                        persistence=True,
                        persistence_type="memory",
                    ),
                ],
            ),
        ],
    )


def create_run_section(
    button_label: str,
    button_id: str,
    status_id: str,
    *,
    status_class_name: str,
    show_initially: bool = False,
):
    return html.Div(
        className="setup-section",
        children=[
            dbc.Button(
                button_label,
                id=button_id,
                color="primary",
                n_clicks=0,
                disabled=True,
                className="primary-action-button",
            ),
            html.Div(
                className="run-feedback-area",
                children=[
                    dcc.Loading(
                        type="dot",
                        color="blue",
                        show_initially=show_initially,
                        children=html.Div(
                            id=status_id,
                            className=(
                                f"small-status {status_class_name}"
                            ),
                        ),
                    )
                ],
            ),
        ],
    )