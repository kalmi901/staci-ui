from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from dash import Input, Output, State, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from src.config import UPLOAD_ROOT
from src.ui import ids
from src.ui.pages.hydraulic_analysis import render_active_model_summary, render_success_alert
from src.services.hydraulic_runner import call_hydraulic_simulator

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
    Output(ids.HYD_DURATION_HOURS, "disabled"),
    Output(ids.HYD_TIMESTEP_MINUTES, "disabled"),
    Input(ids.HYD_OVERRIDE_OPTIONS, "value"),
    )
    def toggle_hydraulic_overrides(enabled):
        disabled = not bool(enabled)
        return disabled, disabled
    
    @app.callback(
        Output(ids.HYD_RUN_STORE, "data"),
        Output(ids.HYD_RUN_STATUS, "children"),
        Input(ids.HYD_RUN_BUTTON, "n_clicks"),
        State(ids.NETWORK_STORE, "data"),
        State(ids.HYD_BACKEND, "value"),
        prevent_initial_call=True)
    def run_hydraulic_simulation(n_clicks, network_state, backend):
        if not n_clicks:
            raise PreventUpdate
        
        if not network_state:
            #raise PreventUpdate
            return no_update, dbc.Alert(
                "No active INP file. Upload a model first",
                color="warning",
                className="upload-alert"
            ) # pyright: ignore[reportCallIssue]
                   
        #inp_path = network_state.get("storage", {}).get("path")
        model_id = network_state["model_id"]
        filename = network_state["filename"]
        
        inp_path = (UPLOAD_ROOT / model_id / Path(filename).name).resolve()
        upload_root = UPLOAD_ROOT.resolve()

        if not inp_path.is_relative_to(upload_root):
            raise ValueError("Invalid uploaded model path.")
        
        if not inp_path:
            return no_update, dbc.Alert(
                "The active model has no stored INP path.",
                color="danger",
                className="upload-alert",
            ) # pyright: ignore[reportCallIssue]
        
        try:
            run_state = call_hydraulic_simulator(
                inp_path,
                model_id=network_state.get("model_id"),
                backend=backend
            )
        except Exception as exc:
            return no_update, dbc.Alert(
                f"Hydraulic simulation failed: {exc}",
                color="danger",
                className="upload-alert",
            )  # pyright: ignore[reportCallIssue]
              
        return run_state, render_success_alert(run_state)