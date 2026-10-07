# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations

from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.development.base_component import Component

from src.ui import ids


def _format_number(
    value,
    *,
    digits: int = 2,
    scale: float = 1.0,
    suffix: str = "",
) -> str:
    if value in (None, ""):
        return "—"

    try:
        number = float(value) * scale
    except (TypeError, ValueError):
        return str(value)

    return f"{number:.{digits}f}{suffix}"


def _metric(label: str, value: str):
    return html.Div(
        className="meta-item",
        children=[
            html.Div(label, className="meta-label"),
            html.Div(value, className="meta-value"),
        ],
    )


def _empty_results():
    return html.Div(
        className="flush-results-placeholder",
        children=[
            html.Div(
                "🚿",
                className="flush-placeholder-icon",
            ),
            html.H3("No flushing plan yet"),
            html.P(
                "Select an active model, enter the hydrant "
                "junction IDs and run STACI Flush."
            ),
        ],
    )


def render_flushing_results(run_state):
    if not run_state:
        return _empty_results()

    plan = run_state.get("plan") or []

    final_coverage = (
        _format_number(
            plan[-1].get("cumulative_volume_percent"),
            digits=1,
            suffix="%",
        )
        if plan
        else "—"
    )

    content: list[Component] = [
        html.Div(
            className="meta-grid flush-meta-grid",
            children=[
                _metric(
                    "Status",
                    str(
                        run_state.get("status", "—")
                    ).title(),
                ),
                _metric(
                    "Scenarios",
                    str(run_state.get("scenario_count", "—")),
                ),
                _metric(
                    "Plan steps",
                    str(
                        run_state.get(
                            "plan_count",
                            len(plan),
                        )
                    ),
                ),
                _metric(
                    "Final coverage",
                    final_coverage,
                ),
            ],
        )
    ]

    if run_state.get("partial"):
        content.append(
            dbc.Alert(
                "The run produced partial results. Invalid scenarios "
                "are excluded from the actionable plan.",
                color="warning",
                className="mt-3",
            )
        )

    if not plan:
        content.append(
            dbc.Alert(
                "No actionable flushing-plan rows were produced.",
                color="secondary",
                className="mt-3",
            )
        )
        return content

    headers = [
        "Rank",
        "Hydrant",
        "Flow [L/s]",
        "Qualifying [m³]",
        "Additional [m³]",
        "Coverage [%]",
        "Travel time [min]",
        "Volume/flow [min]",
        "Status",
    ]

    rows = []

    for row in plan:
        redundant = str(
            row.get("redundant", "0")
        ).lower() in {
            "1",
            "true",
            "yes",
        }

        rows.append(
            html.Tr(
                children=[
                    html.Td(row.get("rank", "—")),
                    html.Td(row.get("node_id", "—")),
                    html.Td(
                        _format_number(
                            row.get("hydrant_flow_m3s"),
                            scale=1000.0,
                        )
                    ),
                    html.Td(
                        _format_number(
                            row.get(
                                "qualifying_volume_m3"
                            )
                        )
                    ),
                    html.Td(
                        _format_number(
                            row.get(
                                "additional_volume_m3"
                            )
                        )
                    ),
                    html.Td(
                        _format_number(
                            row.get(
                                "cumulative_volume_percent"
                            ),
                            digits=1,
                        )
                    ),
                    html.Td(
                        _format_number(
                            row.get("opening_time_min"),
                            digits=1,
                        )
                    ),
                    html.Td(
                        _format_number(
                            row.get(
                                "volume_over_flow_time_min"
                            ),
                            digits=1,
                        )
                    ),
                    html.Td(
                        dbc.Badge(
                            (
                                "Redundant"
                                if redundant
                                else "Selected"
                            ),
                            color=(
                                "secondary"
                                if redundant
                                else "success"
                            ),
                        )
                    ),
                ]
            )
        )

    content.extend(
        [
            html.Div(
                className="flush-plan-table-wrap",
                children=dbc.Table(
                    children=[
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th(header)
                                    for header in headers
                                ]
                            )
                        ),
                        html.Tbody(rows),
                    ],
                    bordered=False,
                    hover=True,
                    responsive=True,
                    striped=True,
                    className="flush-plan-table",
                ),
            ),
            html.Div(
                "Scenario map and velocity inspection will appear "
                "below the plan in the next step.",
                className="soft-panel small-status mt-3",
            ),
        ]
    )

    return content


def _number_field(
    label: str,
    component_id: str,
    value: float,
    *,
    min_value: float | None = 0,
):
    return html.Div(
        children=[
            dbc.Label(label),
            dbc.Input(
                id=component_id,
                type="number",
                value=value,
                min=min_value,
                step="any",
                persistence=True,
                persistence_type="memory",
            ),
        ]
    )


def _create_active_model_section():
    return html.Div(
        className="setup-section",
        children=[
            html.H3("Model summary"),
            html.Div(
                id=ids.FLUSH_ACTIVE_MODEL_SUMMARY,
                className="flush-active-model-box",
                children=[
                    html.Div(
                        "No active model",
                        className="model-summary-title",
                    ),
                    html.P(
                        "Go to Load Model and upload an EPANET .inp "
                        "file first."
                    ),
                ],
            ),
        ],
    )


def _create_hydrant_section():
    return html.Div(
        className="setup-section",
        children=[
            html.H3("Hydrants"),
            html.P(
                "Enter exact junction IDs separated by commas "
                "or new lines."
            ),
            dbc.Label("Hydrant junction IDs"),
            dbc.Textarea(
                id=ids.FLUSH_HYDRANT_IDS,
                placeholder="J101, J205, J310",
                rows=5,
                persistence=True,
                persistence_type="memory",
                className="flush-hydrant-input",
            ),
            dbc.Label("Opening mode", className="mt-3"),
            dcc.Dropdown(
                id=ids.FLUSH_MODE,
                options=[
                    {
                        "label": "One hydrant at a time",
                        "value": "single",
                    },
                    {
                        "label": "All hydrants simultaneously",
                        "value": "multi",
                    },
                ],
                value="single",
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
        ],
    )


def _create_outlet_settings_section():
    return html.Div(
        className="setup-section",
        children=[
            html.H3("Outlet and planning settings"),
            html.P(
                "Define the common hydrant outlet and the velocity "
                "and pressure criteria used by the flushing plan."
            ),
            html.Div(
                className="flush-options-grid",
                children=[
                    _number_field(
                        "Outlet area [m²]",
                        ids.FLUSH_HYDRANT_AREA,
                        0.002,
                    ),
                    _number_field(
                        "Total loss coefficient",
                        ids.FLUSH_LOSS_COEFFICIENT,
                        2.0,
                    ),
                    _number_field(
                        "Velocity threshold [m/s]",
                        ids.FLUSH_VELOCITY_THRESHOLD,
                        0.5,
                    ),
                    _number_field(
                        "Minimum pressure head [m]",
                        ids.FLUSH_MIN_PRESSURE_HEAD,
                        0.0,
                        min_value=None,
                    ),
                ],
            ),
            dbc.Switch(
                id=ids.FLUSH_WRITE_NETWORKS,
                label="Write inspection INP files for each scenario",
                value=False,
                className="mt-3",
                persistence=True,
                persistence_type="memory",
            ),
        ],
    )


def _create_run_section():
    return html.Div(
        className="setup-section",
        children=[
            dbc.Button(
                "Create Flushing Plan",
                id=ids.FLUSH_RUN_BUTTON,
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
                        show_initially=False,
                        children=html.Div(
                            id=ids.FLUSH_RUN_STATUS,
                            className=(
                                "small-status flush-run-status"
                            ),
                        ),
                    )
                ],
            ),
        ],
    )


def _create_setup_card():
    return dbc.Card(
        className="app-card flush-setup-card",
        children=[
            dbc.CardHeader("Flushing Setup"),
            dbc.CardBody(
                children=[
                    _create_active_model_section(),
                    html.Hr(),
                    _create_hydrant_section(),
                    html.Hr(),
                    _create_outlet_settings_section(),
                    html.Hr(),
                    _create_run_section(),
                ]
            ),
        ],
    )


def _create_results_card():
    return dbc.Card(
        className="app-card flush-results-card",
        children=[
            dbc.CardHeader("Flushing Plan"),
            dbc.CardBody(
                id=ids.FLUSH_RESULTS,
                children=_empty_results(),
            ),
        ],
    )


def create_layout():
    return html.Div(
        className="page flush-page",
        children=[
            html.Div(
                className="page-header",
                children=[
                    html.Div(
                        children=[
                            html.H1("Flushing Planning"),
                            html.P(
                                "Evaluate hydrant opening scenarios "
                                "and rank them by additional pipe-volume "
                                "coverage."
                            ),
                        ]
                    ),
                    dbc.Badge(
                        "STACI Flush",
                        color="info",
                        className="page-badge",
                    ),
                ],
            ),
            html.Div(
                className="flush-workspace",
                children=[
                    _create_setup_card(),
                    _create_results_card(),
                ],
            ),
        ],
    )