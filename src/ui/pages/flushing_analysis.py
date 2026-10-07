# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations

from dash import dcc, html
import dash_bootstrap_components as dbc

from src.ui import ids


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
                children=[
                    html.Div(
                        className="flush-results-placeholder",
                        children=[
                            html.Div(
                                "🚿",
                                className="flush-placeholder-icon",
                            ),
                            html.H3("No flushing plan yet"),
                            html.P(
                                "Select an active model, enter the "
                                "hydrant junction IDs and run STACI Flush."
                            ),
                        ],
                    )
                ],
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