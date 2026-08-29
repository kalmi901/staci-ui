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

PLAY_STR  = "▶ Play"
PAUSE_STR = "⏸ Pause"

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
    
    # -- Animation --
    @app.callback(
        Output(ids.HYD_TIME_SLIDER, "min"),
        Output(ids.HYD_TIME_SLIDER, "max"),
        Output(ids.HYD_TIME_SLIDER, "marks"),
        Output(ids.HYD_TIME_SLIDER, "value"),
        Output(ids.HYD_TIME_SLIDER, "disabled"),
        Output(ids.HYD_ANIMATION_INTERVAL, "disabled"),
        Output(ids.HYD_PLAY_BUTTON, "children"),
        Output(ids.HYD_PLAY_BUTTON, "disabled"),
        Input(ids.HYD_RUN_STORE, "data"),
        Input(ids.HYD_PLAY_BUTTON, "n_clicks"),
        Input(ids.HYD_ANIMATION_INTERVAL, "n_intervals"),
        State(ids.HYD_TIME_SLIDER, "value"),
        State(ids.HYD_ANIMATION_INTERVAL, "disabled"),
        prevent_initial_call=True
    )
    def control_hydraulic_time(
        run_state,
        play_clicks,
        n_intervals,
        current_value,
        interval_disabled
    ):
        # Enable / Disable Control
        if not run_state or run_state.get("status") != "success":
            return 0, 0, {0: "0"}, 0, True, True, PLAY_STR, True
        
        time = run_state.get("time", [])
        if not time:
            return 0, 0, {0: "0"}, 0, True, True, PLAY_STR, True
        
        max_index = len(time) - 1
        if max_index <= 0:
            return 0, 0, {0: "0"}, 0, True, True, PLAY_STR, True
        
        # Mark settings
        mark_indices = sorted(
            set(
                [
                    0,
                    max_index,
                    max_index // 4,
                    max_index // 2,
                    (3 * max_index) // 4,
                ]
            )
        )
        
        marks = {
            i: f"{int(time[i] / 3600)} h"
            for i in mark_indices
        }
        
        # -- Handle Inputs --
        # 1) Store Available 
        if ctx.triggered_id == ids.HYD_RUN_STORE:
            print("Control Hydraulic time: HYD_RUN_STORE")
            return 0, max_index, marks, 0, False, True, PLAY_STR, False
        
        # 2) PLAY/PAUSE Button pressed
        if ctx.triggered_id == ids.HYD_PLAY_BUTTON:
            print("Control Hydraulic time: HYD_PLAY_BUTTON")
            should_start = bool(interval_disabled)
            
            if should_start:
                return 0, max_index, marks, current_value or 0, False, False, PAUSE_STR, False
        
            return 0, max_index, marks, current_value or 0, False, True, PLAY_STR, False
        
        # 3) Increse time value
        if ctx.triggered_id == ids.HYD_ANIMATION_INTERVAL:
            print("Control Hydraulic time: HYD_ANIMATION_INTERVAL")
            value = current_value or 0
            value = (value + 1) % max_index
            
            return 0, max_index, marks, value, False, False, PAUSE_STR, False
        
        return 0, max_index, marks, current_value or 0, False, True, PLAY_STR, False