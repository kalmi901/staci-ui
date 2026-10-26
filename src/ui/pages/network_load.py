# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations
from dash import dcc, html
import dash_bootstrap_components as dbc
from typing import Dict, Any

from src.ui import ids
from src.ui.pages.components import (
    create_color_range_control,
    create_metric_item,
    create_page_header,
    render_empty_model_summary
)
from src.visualisation.common import make_empty_network_figure


def _create_preview_toolbar():
    return html.Div(
        className="plot-toolbar",
        children=[
            html.Div(
                className="plot-control",
                children=[
                    dbc.Label("Node attribute"),
                    dcc.Dropdown(
                        id=ids.NODE_COLOR_BY,
                        options=[
                            {"label": "None", "value" : "none"},
                            {"label": "Elevation", "value": "elevation"},
                            {"label": "Demand", "value": "demand"},
                        ],
                        value="none",
                        clearable=False,
                        persistence=True,
                        persistence_type="memory"
                    )
                ]
            ),
            html.Div(
                className="plot-control",
                children=[
                    dbc.Label("Link attribute"),
                    dcc.Dropdown(
                        id=ids.LINK_COLOR_BY,
                        options=[
                            {"label": "None", "value": "none"},
                            {"label": "Length", "value": "length"},
                            {"label": "Diameters", "value": "diameter"},
                            {"label": "Roughness", "value": "roughness"},
                        ],
                        value="none",
                        clearable=False,
                        persistence=True,
                        persistence_type="memory"
                    )
                ]
            ),
            create_color_range_control(
                "Node min / max",
                ids.NODE_COLOR_MIN,
                ids.NODE_COLOR_MAX,
                placeholder_prefix="node",
            ),
            create_color_range_control(
                "Link min / max",
                ids.LINK_COLOR_MIN,
                ids.LINK_COLOR_MAX,
                placeholder_prefix="link",
            ),
        ]
    )

def render_model_summary(network_state: Dict[str, Any] | None):
    if not network_state:
        return render_empty_model_summary(
                "Upload an EPANET .inp file"
            )
    
    summary = network_state.get("summary", {})
    nodes = summary.get("Nodes", {})
    links = summary.get("Links", {})
    spatial = network_state.get("spatial", {})
    status  = network_state.get("status", "uploaded")
    
        
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
                                f"Model ID: {network_state.get('model_id', '—')}",
                                className="small-status",
                            ),
                        ],
                    ),
                    dbc.Badge(
                        status.capitalize(),
                        color="success" if status == "uploaded" else "secondary",
                    ),  # type: ignore
                ],
            ),
            html.Div(
                className="meta-grid",
                children=[
                    create_metric_item(
                        "Junctions",
                        nodes.get("Junctions", "—"),
                    ),
                    create_metric_item(
                        "Pipes",
                        links.get("Pipes", "—"),
                    ),
                    create_metric_item(
                        "Tanks",
                        nodes.get("Tanks", "—"),
                    ),
                    create_metric_item(
                        "Reservoirs",
                        nodes.get("Reservoirs", "—"),
                    ),
                    create_metric_item(
                        "Patterns",
                        summary.get("Patterns", "—"),
                    ),
                    create_metric_item(
                        "Pumps",
                        links.get("Pumps", "—"),
                    ),
                    create_metric_item(
                        "Valves",
                        links.get("Valves", "—"),
                    ),
                    create_metric_item(
                        "Controls",
                        summary.get("Controls", "—"),
                    ),
                ],
            ),
            html.Div(
                className="model-storage-note",
                children=[
                    html.Div(f"Coordinate system: {spatial.get('coordinate_system', '—')}"),
                    html.Div(f"Background mode: {spatial.get('background_mode', '—')}"),
                ],
            ),
        ],
    )

def create_layout():
    return html.Div(
        className="page load-page",
        children=[
            # ----  Header -----
            create_page_header(
                "Load Network Model",
                (
                    "Upload and inspect an EPANET network model for "
                    "analysis using STACI tools."
                ),
                "Model setup",
            ),
            # ---- Workspace ----
            html.Div(
                className="analysis-workspace load-workspace",
                children=[
                    # -- Setup --
                    dbc.Card(
                        className="app-card load-setup-card",
                        children=[
                            dbc.CardHeader("Setup"),
                            dbc.CardBody(
                                children=[
                                    # -- UPLOAD SECTION --
                                    html.Div(
                                        className="setup-section",
                                        children=[
                                            html.H3("Water network model"),
                                            html.P("Choose an EPANET input file."),  # The file will be saved server-side, while the dashboard keeps only a lightweight active-model reference.")

                                            dcc.Upload(
                                                id=ids.UPLOAD_INP,
                                                className="model-upload",
                                                children=html.Div(
                                                    children=[
                                                        html.Div("Drop .inp file here", className="model-upload-title"),
                                                        html.Div("or click to browse", className="model-upload-title")
                                                    ]
                                                ), multiple=False
                                            ),
                                            
                                            html.Div(
                                                id=ids.UPLOAD_STATUS,
                                                className="small-status upload-status",
                                            )   
                                        ]
                                    ), html.Hr(),
                                    # -- MODEL SUMMARY --
                                    html.Div(
                                        className="setup-section",
                                        children=[
                                            html.H3("Active model"),
                                            html.Div(
                                                id=ids.ACTIVE_MODEL_SUMMARY,
                                                children=render_empty_model_summary(
                                                        "Upload an EPANET .inp file"
                                                    )
                                            )
                                        ]
                                    ),
                                    html.P(
                                            id=ids.LOAD_MODEL_STATUS,
                                            className="small-status",
                                            children="",
                                        ),
                                ]
                            )
                        ]
                    ),
                    # -- Network Preview --
                    dbc.Card(
                        className="app-card load-preview-card",
                        children=[
                            dbc.CardHeader("Network Preview"),
                            dbc.CardBody(
                                children=[
                                    _create_preview_toolbar(),
                                    dcc.Graph(
                                        id=ids.NETWORK_GRAPH,
                                        className="network-graph",
                                        config={"displaylogo": False},
                                        figure=make_empty_network_figure()
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
        ]
    )