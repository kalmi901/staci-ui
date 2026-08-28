# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations
from dash import dcc, html
import dash_bootstrap_components as dbc
from typing import Dict, Any

from src.ui import ids
from src.visualisation.network_preview import make_empty_network_figure



def render_active_model_summary(network_state):
    if not network_state:
        return html.Div(
            className="hyd-active-model-box",
            children=[
                html.Div("No active model", className="model-summary-title"),
                html.P("Go to Load Model and upload an EPANET .inp file first."),
            ]
        )
        
    summary = network_state.get("summary", {})
    nodes   = summary.get("Nodes", {})
    links   = summary.get("Links", {})
    
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
                                className="model-summary-title"
                            ),
                            html.Div(
                                f"Model ID: {network_state.get("model_id", "—")}",
                                className="small-status"
                            )
                        ]
                    ),
                    dbc.Badge("Model Ready", color="success")
                ]
            ),
            html.Div(
                className="model-storage-note",
                children=[
                    html.Div(
                        f"Junctions: {nodes.get('Junctions', '—')} · "
                        f"Tanks: {nodes.get('Tanks', '—')} · "
                        f"Reservoirs: {nodes.get('Reservoirs', '—')}"
                    ),
                    html.Div(
                        f"Pipes: {links.get('Pipes', '—')} · "
                        f"Pumps: {links.get('Pumps', '—')} · "
                        f"Valves: {links.get('Valves', '—')}"
                    ),
                ],
            )
        ]
    )

def render_success_alert(run_state: Dict[str, Any]):
    summary = run_state.get("summary", {})
    #pressure = summary.get("pressures", {})
    #flowrate = summary.get("flowrater", {})
    
    return dbc.Alert(
        children=[
            html.Div("Hydraulic simulation finished.", style={"fontWeight": 800}),
            html.Div(
                f"Run ID: {run_state.get('run_id', '—')} · "
                f"Backend: {run_state.get("backend", '—')} · "
                f"Time steps: {summary.get('n_steps', '—')} · "
            )
        ],
        color="success",
        className="upload-alert"
    )


# Setup Card
def _create_setup_card():
    
    def _create_active_model_section():
        return html.Div(
        className="setup-section",
        children=[
            html.H3("Model Summary"),
            html.Div(
                id=ids.HYD_ACTIVE_MODEL_SUMMARY,
                className="hyd-active-model-box",
                children=[
                    html.Div("No active model", className="model-summary-title"),
                    html.P("Go to Load Model and upload an EPANET .inp file first."),
                ]
            ),
        ],
    )
    
    def _create_backend_selection():
        return html.Div(
            className="setup-section",
            children=[
                html.H3("Simulation backend"),
                html.P(
                    "Choose which hydraulic solver backend should run the active model."
                ),
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
                html.H3("Simulation Options"),
                html.P(
                    "Use INP settings by default. Enable overrides to run a scenario "
                    "with modified timing, demand, or solver settings."
                ),
                dbc.Switch(
                    id=ids.HYD_OVERRIDE_OPTIONS,
                    label="Enable simulation option override",
                    value=False,
                    className="hyd-override-switch"
                ),
                html.Div(
                    className="hyd-options-grid",
                    children=[
                        html.Div(
                            children=[
                                dbc.Label("Duration [h]"),
                                dbc.Input(
                                    id=ids.HYD_DURATION_HOURS,
                                    type="number",
                                    min=0,
                                    step=1,
                                    value=24,
                                    disabled=True
                                )
                            ]
                        ),
                        html.Div(
                            children=[
                                dbc.Label("Hydraulic timestep [min]"),
                                dbc.Input(
                                    id=ids.HYD_TIMESTEP_MINUTES,
                                    type="number",
                                    min=0,
                                    step=1,
                                    value=60,
                                    disabled=True
                                )
                            ]
                        )  
                    ]
                )
            ]
        )
    
    def _create_run_section():
        return html.Div(
            className="setup-section",
            children=[
                dbc.Button(
                    "Run Hydraulic Simulation",
                    id=ids.HYD_RUN_BUTTON,
                    color="primary",
                    n_clicks=0,
                    disabled=True,
                    className="primary-action-button"
                ),
                html.Div(
                    className="run-feedback-area",
                    children=[
                        dcc.Loading(
                            type="dot",
                            color="#137fc4",
                            children=html.Div(
                                id=ids.HYD_RUN_STATUS,
                                className="small-status hyd-run-status",
                                children="Upload a network model first.",
                            )
                        )
                    ]
                )
            ]
        )
    
    return dbc.Card(
        className="app-card hydro-setup-card",
        children=[
            dbc.CardHeader("EPS Simulation Setup"),
            dbc.CardBody(
                children=[
                    _create_active_model_section(),
                    html.Hr(),
                    _create_backend_selection(),
                    html.Hr(),
                    _create_simulation_options(),
                    html.Hr(),
                    _create_run_section()
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
                               {"label": "Pressure", "value": "pressure"},
                               {"label": "Head", "value": "head"},
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
                                {"label": "Headloss", "value": "headloss"},
                                {"label": "Status", "value": "status"}
                            ],
                            value="flowrate",
                            clearable=False,
                            persistence=True,
                            persistence_type="memory"
                        )
                    ]
                ),
                html.Div(
                    className="plot-control color-range-inputs",
                    children=[
                        dbc.Label("Node min / max"),
                        html.Div(
                            className="color-range-row",
                            children=[
                                dbc.Input(
                                    id=ids.HYD_NODE_COLOR_MIN,
                                    type="number",
                                    placeholder="node-min",
                                    disabled=True
                                ),
                                dbc.Input(
                                    id=ids.HYD_NODE_COLOR_MAX,
                                    type="number",
                                    placeholder="node-max",
                                    disabled=True
                                ),
                            ]
                        )
                    ]
                ),
                html.Div(
                    className="plot-control color-range-inputs",
                    children=[
                        dbc.Label("Link min / max"),
                        html.Div(
                            className="color-range-row",
                            children=[
                                dbc.Input(
                                    id=ids.HYD_LINK_COLOR_MIN,
                                    type="number",
                                    placeholder="link-min",
                                    disabled=True
                                ),
                                dbc.Input(
                                    id=ids.HYD_LINK_COLOR_MAX,
                                    type="number",
                                    placeholder="link-max",
                                    disabled=True
                                ),
                            ]
                        )
                    ]
                )
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
            dbc.CardHeader("Hydraulic network result"),
            dbc.CardBody(
                children=[
                    _create_plot_toolbar(),
                    dcc.Graph(
                            id=ids.HYD_NETWORK_GRAPH,
                            className="network-graph",
                            config={"displaylogo": False},
                            figure=make_empty_network_figure(
                                "Run a hydraulic simulation to view animated network results."
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
            html.Div(
                className="page-header",
                children=[
                    html.Div(
                        children=[
                            html.H1("Hydraulic Simulations"),
                            html.P(
                                "Run hydraulic simulations for the active WN model "
                                "and inspect time-dependent node and link results."
                            )
                        ]
                    ),
                    dbc.Badge("Hydraulic Analysis", color="info", className="page-badge")
                ]
            ),
            # ---- Workspace ---
            html.Div(
                className="hydro-workspace",
                children=[
                    _create_setup_card(),
                    _create_network_results_card()
                ]
            ),
            #html.H2("TODO: create_results_card")
        ]
    )