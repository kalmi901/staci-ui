# pyright: reportCallIssue=false 
from __future__ import annotations
from dash import Input, Output, html
import dash_bootstrap_components as dbc

from src.ui import ids
from src.ui.paths import local_path
from src.ui.pages import(
    home,
    network_load,
    network_partitioning,
    hydraulic_analysis,
    flushing_analysis
)

def _not_found_page(pathname: str | None):
    route = pathname or "/"

    return html.Div(
        className="page not-found-page",
        children=[
            html.Div(
                className="page-header",
                children=[
                    html.Div(
                        children=[
                            html.H1("Page not found"),
                            html.P(f"Unknown route: {route}"),
                        ]
                    )
                ],
            )
        ],
    )
    
    
def register_routing_callbacks(app):
    @app.callback(Output(ids.PAGE_CONTENT, "children"), Input(ids.URL, "pathname"))
    def route(pathname):
        pathname = local_path(pathname)
        if pathname in (None, "", "/"):
            return home.create_layout()
        elif pathname == "/network/load":
            return network_load.create_layout()
        elif pathname == "/analysis/partitioning":
            return network_partitioning.create_layout()
        elif pathname == "/analysis/hydraulic":
            return hydraulic_analysis.create_layout()
        elif pathname == "/analysis/flushing":
            return flushing_analysis.create_layout()
        
        return _not_found_page(pathname)
