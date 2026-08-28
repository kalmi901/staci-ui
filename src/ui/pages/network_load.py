# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations
from dash import dcc, html
import dash_bootstrap_components as dbc
from typing import Dict, Any

from src.ui import ids
from src.visualisation.network_preview import make_empty_network_figure


def _empty_summary():
    return html.Div(
        className="model-summary-empty",
        children=[
            html.Div("No active model", className="model-summary-title"),
            html.P("Upload an EPANET .inp file")
        ]
    )

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
                            {"label": "Type", "value": "type"}
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
                            {"label": "Type", "value": "type"}
                        ],
                        value="none",
                        clearable=False,
                        persistence=True,
                        persistence_type="memory"
                    )
                ]
            )
        ]
    )

def render_model_summary(network_state: Dict[str, Any] | None):
    if not network_state:
        return _empty_summary()
    
    summary = network_state.get("summary", {})
    nodes = summary.get("Nodes", {})
    links = summary.get("Links", {})
    spatial = network_state.get("spatial", {})
    storage = network_state.get("storage", {})
    status  = network_state.get("status", "uploaded")
    
    def _tile(label, value):
        return html.Div(
            className="meta-item",
            children=[
                html.Div(label, className="meta-label"),
                html.Div(str(value), className="meta-value")
            ]
        )
        
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
                    _tile("Junctions", nodes.get("Junctions", "—")),
                    _tile("Pipes", links.get("Pipes", "—")),
                    _tile("Tanks", nodes.get("Tanks", "—")),
                    _tile("Reservoirs", nodes.get("Reservoirs", "—")),
                    _tile("Patterns", summary.get("Patterns", "—")),
                    _tile("Pumps", links.get("Pumps", "—")),
                    _tile("Valves", links.get("Valves", "—")),
                    _tile("Controls", summary.get("Controls", "—")),
                ],
            ),
            html.Div(
                className="model-storage-note",
                children=[
                    html.Div(f"Stored at: {storage.get('path', '—')}"),
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
            html.Div(
                className="page-header",
                children=[
                    html.Div(
                        children=[
                            html.H1("Load Network Model"),
                            html.P(
                                "Upload, and inspect an EPANET network model for later hydraulic, "
                                "quality and biofilm analysis."
                            )
                        ]
                    ),
                    dbc.Badge("Model setup", color="info", className="page-badge")
                ]
            ),
            # ---- Workspace ----
            html.Div(
                className="load-workspace",
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
                                                #children="No file uploaded yet"
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
                                                children=_empty_summary()
                                            )
                                        ]
                                    ),
                                    # --TODO --> coordinate system, map overlay etc.
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
                                        className="network-grap",
                                        config={"displaylogo": False},
                                        figure=make_empty_network_figure()
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            # -- Property Inspector ---
            dbc.Card(
                className="app-card inspector-card",
                children = [html.P("Property Inspector")]
            )
        ]
    )