from __future__ import annotations
from dash import dcc, html

from src.ui import ids
from src.ui.sidebar import create_sidebar

def create_app_shell():
    return html.Div(
        className="app-shell",
        children=[
            dcc.Location(id=ids.URL),
            dcc.Store(id=ids.NETWORK_STORE, storage_type="memory"),
            dcc.Store(id=ids.NETWORK_VIEW_STORE, storage_type="memory"),
            dcc.Store(id=ids.HYD_RUN_STORE, storage_type="memory"),
            dcc.Store(id=ids.PART_RUN_STORE, storage_type="memory"),
            create_sidebar(),
            html.Main(id=ids.PAGE_CONTENT, className="page-content")
        ]
    )