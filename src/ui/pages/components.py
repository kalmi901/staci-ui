# pylint: disable=not-callable
# pyright: reportCallIssue=false
# Collection of common UI components
from __future__ import annotations
from dash import html
import dash_bootstrap_components as dbc


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