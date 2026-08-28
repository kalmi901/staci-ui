from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from dash import Input, Output, State, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from src.ui import ids
from src.ui.pages.hydraulic_analysis import render_active_model_summary


def register_hydraulic_callbacks(app):
    
    @app.callback(
        Output(ids.HYD_ACTIVE_MODEL_SUMMARY, "children"),
        Output(ids.HYD_RUN_BUTTON, "disabled"),
        Input(ids.NETWORK_STORE, "data"),
    )
    def sync_hydraulic_active_model(network_state):
        if not network_state:
            return render_active_model_summary(network_state), True
        
        return render_active_model_summary(network_state), False
    
    
    @app.callback(
        #Output(ids.HYD_RUN_STORE, "data"),
        #Output(ids.HYD_RUN_STATUS, "children"),
        Input(ids.HYD_RUN_BUTTON, "n_clicks"),
        State(ids.NETWORK_STORE, "data"),
        State(ids.HYD_BACKEND, "value"),
        prevent_initial_call=True)
    def run_hydraulic_simulation(n_clicks, network_state, backend):
        if not n_clicks:
            raise PreventUpdate
        
        if not network_state:
            return no_update, dbc.Alert(
                "No active INP file. Upload a model first",
                color="warning",
                className="upload-alert"
            ) # pyright: ignore[reportCallIssue]
            
        print("run-hydraulic-simulation")