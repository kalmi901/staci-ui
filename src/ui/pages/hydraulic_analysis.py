# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations
from dash import dcc, html
import dash_bootstrap_components as dbc
from typing import Dict, Any

from src.ui import ids
from src.ui.pages.components import (
    create_active_model_section,
    create_color_range_control,
    create_network_display_controls,
    create_number_field,
    create_page_header,
    create_run_section,
    create_settings_grid
)
from src.visualisation.common import make_empty_network_figure


def render_success_alert(run_state: Dict[str, Any]):
    summary = run_state.get("summary", {})
    failed_frames = int(summary.get("failed_frames", 0) or 0)
    
    return dbc.Alert(
        children=[
            html.Div(
                "Hydraulic simulation finished with warnings." 
                if failed_frames
                else "Hydraulic simulation finished.", style={"fontWeight": 800}),
            html.Div(
                f"Run ID: {run_state.get('run_id', '—')} · "
                f"Backend: {run_state.get("backend", '—')} · "
                f"Time steps: {summary.get('n_steps', '—')} · "
            ),
            html.Div(
                (
                    f"{failed_frames} time step did not converge."
                    if failed_frames == 1
                    else (
                        f"{failed_frames} time steps "
                        "did not converge."
                    )
                ),
                className="mt-1",
            ) if failed_frames else None,
        ],
        color="warning" if failed_frames else "success",
        className="upload-alert"
    )


# Setup Card
def _create_setup_card():
    def _create_backend_selection():
        return html.Div(
            className="setup-section",
            children=[
                html.H3("Simulation backend"),
                html.P("Select the hydraulic solver for the active model."),
                dcc.Dropdown(
                    id=ids.HYD_BACKEND,
                    options=[
                        {
                            "label" : "WNTR Simulator",
                            "value" : "wntr",
                            "disabled" : False
                        },
                        {
                            "label" : "STACI EPS",
                            "value" : "staci",
                            "disabled" : False
                        }
                    ],
                    value="staci",
                    clearable=False,
                    persistence=True,
                    persistence_type="memory"
                )
            ]
        )
    
    def _create_simulation_options():
        return html.Div(
            className="setup-section",
            children=[
                html.H3("Simulation options"),
                html.P("Use the INP settings by default, or override the timing and demand multiplier below."),
                dbc.Switch(
                    id=ids.HYD_OVERRIDE_OPTIONS,
                    label="Override INP simulation options",
                    value=False,
                    className="hyd-override-switch"
                ),
                create_settings_grid(
                    [
                        create_number_field(
                            "Duration [h]",
                            ids.HYD_DURATION_HOURS,
                            24,
                            min_value=1,
                            step=1,
                            disabled=True,
                            persist=False,
                        ),
                        create_number_field(
                            "Hydraulic timestep [min]",
                            ids.HYD_TIMESTEP_MINUTES,
                            5,
                            min_value=0,
                            step=1,
                            disabled=True,
                            persist=False,
                        ),
                        create_number_field(
                            "Report timestep [min]",
                            ids.HYD_REPORT_TIMESTEP_MINUTES,
                            60,
                            min_value=1,
                            step=1,
                            disabled=True,
                            persist=False,
                        ),
                        create_number_field(
                            "Rule timestep [min]",
                            ids.HYD_RULE_TIMESTEP_MINUTES,
                            5,
                            min_value=1,
                            step=1,
                            disabled=True,
                            persist=False,
                        ),
                        create_number_field(
                            "Demand multiplier [-]",
                            ids.HYD_DEMAND_MULTIPLIER,
                            1.0,
                            min_value=0,
                            step=0.1,
                            disabled=True,
                            persist=False,
                        ),
                    ]
                )
            ]
        )
    
    
    return dbc.Card(
        className="app-card hydro-setup-card",
        children=[
            dbc.CardHeader("Hydraulic simulation setup"),
            dbc.CardBody(
                children=[
                    create_active_model_section(
                        ids.HYD_ACTIVE_MODEL_SUMMARY,
                    ),
                    html.Hr(),
                    _create_backend_selection(),
                    html.Hr(),
                    _create_simulation_options(),
                    html.Hr(),
                    create_run_section(
                        "Run hydraulic simulation",
                        ids.HYD_RUN_BUTTON,
                        ids.HYD_RUN_STATUS,
                        status_class_name="hyd-run-status",
                        show_initially=True,
                    ),
                ]
            )
        ]
    )

# Network Results Card
def _create_network_results_card():
    def _create_plot_toolbar():
        return html.Div(
            className="plot-toolbar",
            children=[
                html.Div(
                    className="plot-control",
                    children=[
                        dbc.Label("Node result"),
                        dcc.Dropdown(
                           id=ids.HYD_NODE_RESULT,
                           options=[
                               {"label": "Pressure head", "value": "pressure"},
                               {"label": "Total head", "value": "head"},
                               {"label": "Demand", "value": "demand"}
                           ],
                           value="pressure",
                           clearable=False,
                           persistence=True,
                           persistence_type="memory"
                        )
                    ]
                ),
                html.Div(
                    className="plot-control",
                    children=[
                        dbc.Label("Link result"),
                        dcc.Dropdown(
                            id=ids.HYD_LINK_RESULT,
                            options=[
                                {"label": "Flow rate", "value": "flowrate"},
                                {"label": "Velocity", "value": "velocity"},
                                {"label": "Head loss", "value": "headloss"},
                            ],
                            value="flowrate",
                            clearable=False,
                            persistence=True,
                            persistence_type="memory"
                        )
                    ]
                ),
                create_color_range_control(
                    "Node min / max",
                    ids.HYD_NODE_COLOR_MIN,
                    ids.HYD_NODE_COLOR_MAX,
                    placeholder_prefix="node",
                ),
                create_color_range_control(
                    "Link min / max",
                    ids.HYD_LINK_COLOR_MIN,
                    ids.HYD_LINK_COLOR_MAX,
                    placeholder_prefix="link",
                ),
                create_network_display_controls(
                    ids.HYD_LINE_WIDTH,
                    ids.HYD_MARKER_SIZE,
                    ids.HYD_HIDE_NODES,
                ),
            ]
        )
    
    def _create_time_controls():
        return html.Div(
            className="hyd-time-controls soft-panel",
            children=[
                html.Div(
                    className="hyd-time-header",
                    children=[
                        dbc.Button(
                            "▶ Play",
                            id=ids.HYD_PLAY_BUTTON,
                            color="secondary",
                            outline=True,
                            size="sm",
                            disabled=True
                        ),
                        html.Div("Time step", className="hyd-time-label"),
                    ]
                ),
                dcc.Slider(
                    id=ids.HYD_TIME_SLIDER,
                    min=0,
                    max=0,
                    step=1,
                    value=0,
                    marks={0: 0},
                    disabled=True
                ),
                dcc.Interval(
                    id=ids.HYD_ANIMATION_INTERVAL,
                    interval=700,
                    n_intervals=0,
                    disabled=True
                )
            ]
        )
    
    return dbc.Card(
        className="app-card hydro-preview-card",
        children=[
            dbc.CardHeader("Hydraulic results"),
            dbc.CardBody(
                children=[
                    _create_plot_toolbar(),
                    dcc.Graph(
                            id=ids.HYD_NETWORK_GRAPH,
                            className="network-graph",
                            config={"displaylogo": False},
                            figure=make_empty_network_figure(
                                "Run a hydraulic simulation to view time-dependent network results.",
                                icon="💧",
                                title="No hydraulic results yet"
                            ),
                    ),
                    _create_time_controls()
                ]
            )
        ]
    )


def create_layout():
    return html.Div(
        className="page hydro-page",
        children=[
            # ---- Header ----
            create_page_header(
                "Hydraulic simulation",
                (
                    "Run a hydraulic simulation for the active water network "
                    "and inspect time-dependent node and link results."
                ),
                "Hydraulic analysis",
            ),
            # ---- Workspace ---
            html.Div(
                className="analysis-workspace hydro-workspace",
                children=[
                    _create_setup_card(),
                    _create_network_results_card()
                ]
            ),
        ]
    )