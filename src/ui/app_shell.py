from __future__ import annotations

from dash import dcc, html

from src.ui import ids
from src.ui.sidebar import create_sidebar


def create_app_shell():
    return html.Div(
        className="app-shell",
        children=[
            dcc.Location(id=ids.URL),
            dcc.Interval(id=ids.SOLVER_STATUS_INTERVAL, interval=2_000, n_intervals=0),
            dcc.Store(id=ids.NETWORK_STORE, storage_type="memory"),
            dcc.Store(id=ids.NETWORK_VIEW_STORE, storage_type="memory"),
            dcc.Store(id=ids.HYD_JOB_REQUEST_STORE, storage_type="memory"),
            dcc.Store(id=ids.HYD_RUN_STORE, storage_type="memory"),
            dcc.Store(id=ids.PART_JOB_REQUEST_STORE, storage_type="memory"),
            dcc.Store(id=ids.PART_RUN_STORE, storage_type="memory"),
            dcc.Store(id=ids.FLUSH_JOB_REQUEST_STORE, storage_type="memory"),
            dcc.Store(id=ids.FLUSH_RUN_STORE, storage_type="memory"),
            dcc.Store(id=ids.CAL_SNAPSHOT_STORE, storage_type="memory"),
            dcc.Store(id=ids.CAL_MEASUREMENT_STORE, storage_type="memory"),
            dcc.Store(id=ids.CAL_JOB_REQUEST_STORE, storage_type="memory"),
            dcc.Store(id=ids.CAL_RUN_STORE, storage_type="memory"),
            create_sidebar(),
            html.Main(id=ids.PAGE_CONTENT, className="page-content"),
        ],
    )
