from __future__ import annotations
from dash import Input, Output, State, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from src.ui import ids
from src.ui.pages.components import render_active_model_summary
from src.ui.pages.hydraulic_analysis import render_success_alert
from src.services.hydraulic_runner import call_hydraulic_simulator
from src.services.model_storage import resolve_uploaded_model
from src.services.inp_model_reader import read_model_options
from src.visualisation.network_preview import make_hydraulic_timestep_figure

import logging
logger = logging.getLogger(__name__)

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
    Output(ids.HYD_DURATION_HOURS, "value"),
    Output(ids.HYD_TIMESTEP_MINUTES, "value"),
    Input(ids.NETWORK_STORE, "data")
    )
    def render_simulation_options(
        network_state
    ):
        if not network_state:
            return None, None
        
        try:
            inp_path = resolve_uploaded_model(
                network_state["model_id"],
                network_state["filename"]
            )
            options = read_model_options(inp_path)
            duration_h = options["duration"] / 3600                     # seconds --> hours
            hydraulic_timestep = options["hydraulic_timestep"] / 60     # seconds --> minutes
            
            return duration_h, hydraulic_timestep        
        
        except Exception:
            logger.exception(
                "Failed to read hydraulic options: model_id=%s",
                network_state.get("model_id", ""),
            )
            return None, None  
    
    @app.callback(
        Output(ids.HYD_RUN_STORE, "data"),
        Output(ids.HYD_RUN_STATUS, "children"),
        Input(ids.HYD_RUN_BUTTON, "n_clicks"),
        State(ids.NETWORK_STORE, "data"),
        State(ids.HYD_BACKEND, "value"),
        State(ids.HYD_OVERRIDE_OPTIONS, "value"),
        State(ids.HYD_DURATION_HOURS, "value"),
        State(ids.HYD_TIMESTEP_MINUTES, "value"),
        prevent_initial_call=True)
    def run_hydraulic_simulation(
        n_clicks,
        network_state,
        backend,
        override_enabled,
        duration,
        hydraulic_timestep):
        if not n_clicks:
            raise PreventUpdate
        
        if not network_state:
            #raise PreventUpdate
            return None, dbc.Alert(
                "No active INP file. Upload a model first",
                color="warning",
                className="upload-alert"
            ) # pyright: ignore[reportCallIssue]
                   
        try:
            inp_path = resolve_uploaded_model(
                network_state["model_id"],
                network_state["filename"]
            )
            
            option_overrides = None
            if override_enabled:
                if duration is None or hydraulic_timestep is None:
                    raise ValueError(
                        "Duration and hydraulic timestep are required when overrides are enabled"
                    )
                if duration < 0:
                    raise ValueError("Duration must be non-negative")
                if hydraulic_timestep <= 0:
                    raise ValueError("Hydraulic timestep must be greater than zero.")
                
                option_overrides = {
                    "duration" : duration * 3600,                   # hours --> seconds
                    "hydraulic_timestep" : hydraulic_timestep * 60  # minutes --> seconds
                }
        
            logger.info(
                "Hydraulic simulation started: model_id=%s, backend=%s",
                network_state.get("model_id"),
                backend
            )
        
            run_state = call_hydraulic_simulator(
                inp_path,
                model_id=network_state.get("model_id", ""),
                backend=backend,
                option_overrides=option_overrides
            )
            
            logger.info(
                "Hydraulic simulation finished: model_id=%s, run_id=%s, backend=%s",
                run_state.get("model_id", ""),
                run_state.get("run_id", ""),
                run_state.get("backend", "")
            )
            
        except Exception as exc:
            logger.exception(
                "Hydraulic simulation failed: model_id=%s",
                network_state.get("model_id", "")
            )
            return None, dbc.Alert(
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
        Input(ids.URL, "pathname"),
        Input(ids.HYD_RUN_STORE, "data"),
        Input(ids.HYD_PLAY_BUTTON, "n_clicks"),
        Input(ids.HYD_ANIMATION_INTERVAL, "n_intervals"),
        State(ids.HYD_TIME_SLIDER, "value"),
        State(ids.HYD_ANIMATION_INTERVAL, "disabled")
    )
    def control_hydraulic_time(
        pathname,
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
            return 0, max_index, marks, 0, False, True, PLAY_STR, False
        
        # 2) PLAY/PAUSE Button pressed
        if ctx.triggered_id == ids.HYD_PLAY_BUTTON:
            should_start = bool(interval_disabled)
            
            if should_start:
                return 0, max_index, marks, current_value or 0, False, False, PAUSE_STR, False
        
            return 0, max_index, marks, current_value or 0, False, True, PLAY_STR, False
        
        # 3) Increse time value
        if ctx.triggered_id == ids.HYD_ANIMATION_INTERVAL:
            value = current_value or 0
            value = (value + 1) % (max_index + 1)
            
            return 0, max_index, marks, value, False, False, PAUSE_STR, False
        
        return 0, max_index, marks, current_value or 0, False, True, PLAY_STR, False
    
    @app.callback(
        Output(ids.HYD_NODE_COLOR_MIN, "value"),
        Output(ids.HYD_NODE_COLOR_MAX, "value"),
        Output(ids.HYD_NODE_COLOR_MIN, "disabled"),
        Output(ids.HYD_NODE_COLOR_MAX, "disabled"),
        Output(ids.HYD_LINK_COLOR_MIN, "value"),
        Output(ids.HYD_LINK_COLOR_MAX, "value"),
        Output(ids.HYD_LINK_COLOR_MIN, "disabled"),
        Output(ids.HYD_LINK_COLOR_MAX, "disabled"),
        Input(ids.HYD_RUN_STORE, "data"),
        Input(ids.HYD_NODE_RESULT, "value"),
        Input(ids.HYD_LINK_RESULT, "value"),
        prevent_initial_call=True
    )
    def sync_hydraulic_color_range(
        run_state,
        node_result,
        link_result
    ):       
        if not run_state or run_state.get("status") != "success":
            return (
                None, None, True, True,
                None, None, True, True,
            )
    
        ranges = run_state.get("ranges", {})
        
        def _get_range(attribute):
            info = ranges.get(attribute, {})
            vmin = info.get("min")
            vmax = info.get("max")
            disabled = vmin is None or vmax is None

            return vmin, vmax, disabled, disabled
        
        node_values = _get_range(node_result)
        link_values = _get_range(link_result)
        
        if ctx.triggered_id == ids.HYD_NODE_RESULT:
            return *node_values, no_update, no_update, no_update, no_update
        
        if ctx.triggered_id == ids.HYD_LINK_RESULT:
            return no_update, no_update, no_update, no_update, *link_values
        
        return *node_values, *link_values

    
    @app.callback(
        Output(ids.HYD_NETWORK_GRAPH, "figure"),
        Input(ids.HYD_RUN_STORE, "data"),
        Input(ids.HYD_TIME_SLIDER, "value"),
        Input(ids.HYD_NODE_RESULT, "value"),
        Input(ids.HYD_LINK_RESULT, "value"),
        Input(ids.HYD_NODE_COLOR_MIN, "value"),
        Input(ids.HYD_NODE_COLOR_MAX, "value"),
        Input(ids.HYD_LINK_COLOR_MIN, "value"),
        Input(ids.HYD_LINK_COLOR_MAX, "value"),
        State(ids.NETWORK_VIEW_STORE, "data")
    )
    def render_hydraulic_network_graph(
        run_state,
        time_index,
        node_result,
        link_result,
        node_cmin,
        node_cmax,
        link_cmin,
        link_cmax,
        network_view_state
    ):  
        return make_hydraulic_timestep_figure(
            network_view_state=network_view_state,
            run_state=run_state,
            time_index=time_index,
            node_result=node_result,
            link_result=link_result,
            node_cmin=node_cmin,
            node_cmax=node_cmax,
            link_cmin=link_cmin,
            link_cmax=link_cmax   
        )