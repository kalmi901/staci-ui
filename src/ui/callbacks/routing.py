# pyright: reportCallIssue=false 
from __future__ import annotations
from dash import Input, Output, html
import dash_bootstrap_components as dbc

from src.ui import ids
from src.ui.pages import(
    home,
    network_load
)

def _placeholder_page(title: str, subtitle: str):
    return html.Div(
        className="page",
        children=[
            html.Div(
                className="page-header",
                children=[
                    html.Div(children=[html.H1(title), html.P(subtitle)]),
                    dbc.Badge("Coming next", color="secondary", className="page-badge"),    # type: ignore
                ],
            ),
            dbc.Card(
                className="app-card",
                children=[
                    dbc.CardHeader("Placeholder"),
                    dbc.CardBody(
                        children=[
                            html.P("Ez az oldal még csak routing placeholder."),
                            html.P("Ugyanazt a sablont fogja használni, mint a Hydraulic analysis: settings + preview + run + results."),
                        ]
                    ),
                ],
            ),
        ],
    )
    
    
def register_routing_callbacks(app):
    @app.callback(Output(ids.PAGE_CONTENT, "children"), Input(ids.URL, "pathname"))
    def route(pathname):
        if pathname in (None, "", "/"):
            return home.create_layout()
        elif pathname == "/network/load":
            return network_load.create_layout()
        elif pathname == "/analysis/hydraulic":
            return _placeholder_page("Analysis · Hydraulic", "Extended-period simulation and results will be placed here.")
        elif pathname == "/analysis/quality":
            return _placeholder_page("Analysis · Quality", "Water quality simulation settings and results will be placed here.")
        elif pathname == "/analysis/biofilm":
            return _placeholder_page("Analysis · Biofilm", "Biofilm solver settings and animated results will be placed here.")
        
        return _placeholder_page("404", f"Unknown route: {pathname}")