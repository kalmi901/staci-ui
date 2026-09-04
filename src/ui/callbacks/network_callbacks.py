from __future__ import annotations
import base64
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dash import Input, Output, State, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from src.ui import ids
from src.services.model_storage import resolve_uploaded_model
from src.services.inp_model_reader import read_model_summary, read_water_network_model
from src.ui.pages.network_load import render_model_summary
from src.visualisation.network_preview import make_node_preview_figure
from src.config import UPLOAD_ROOT

import logging
logger = logging.getLogger(__name__)

def _safe_filename(filename: str) -> str:
    name = Path(filename or "network.inp").name
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
    return name or "network.inp"

def _decode_upload(contents: str) -> bytes:
    if not contents:
        raise ValueError("Missing upload contents.")

    _header, encoded = contents.split(",", 1)
    return base64.b64decode(encoded)

def _save_uploaded_file(filename: str, file_bytes: bytes) -> dict:
    model_id = uuid.uuid4().hex[:12]
    safe_name = _safe_filename(filename)

    model_dir = UPLOAD_ROOT / model_id
    model_dir.mkdir(parents=True, exist_ok=True)

    stored_path = model_dir / safe_name
    stored_path.write_bytes(file_bytes)

    return {
        "model_id": model_id,
        "filename": safe_name,
        "path": str(stored_path),
        "size_bytes": len(file_bytes),
    }
    
def register_network_callbacks(app):
    
    @app.callback(
        Output(ids.NETWORK_STORE, "data"),
        Output(ids.UPLOAD_STATUS, "children"),
        Output(ids.HYD_RUN_STORE, "data", allow_duplicate=True),
        Output(ids.PART_RUN_STORE, "data", allow_duplicate=True),
        Input(ids.UPLOAD_INP, "contents"),
        State(ids.UPLOAD_INP, "filename"),
        State(ids.NETWORK_STORE, "data"),
        prevent_initial_call=True,
    )
    def sync_upload_model(
        contents,
        filename,
        current_network_state
    ):
        triggered_id = ctx.triggered_id
        
        if triggered_id == ids.UPLOAD_INP:
            if not contents:
                raise PreventUpdate
        
        if not filename or not filename.lower().endswith(".inp"):
            return (
                None, 
                dbc.Alert(
                    "Please upload an EPANET .inp file.",
                    color="warning",
                    className="upload-alert"
                ), # pyright: ignore[reportCallIssue]
                None, None
                )
        try:
            file_bytes = _decode_upload(contents)
            saved = _save_uploaded_file(filename, file_bytes)
        except Exception as exc:
            logger.exception(
                "Model upload failed: filename=%s",
                filename
            )
            return(
                None,
                dbc.Alert(
                    f"Upload failed: {exc}",
                    color="danger",
                    className="upload-alert",
                ), # pyright: ignore[reportCallIssue]
                None, None
            )
        
        summary = {}
        try:
            summary = read_model_summary(saved["path"])
        except Exception as e:
            logger.exception(
                "Model load failed: filename=%s",
                filename
            )
            return (
                None, 
                dbc.Alert(
                    f"Model load failed: {e}",
                    color="danger",
                    className="upload-alert",
                ), # pyright: ignore[reportCallIssue]
                None, None
            )
        network_state = {
            "model_id" : saved["model_id"],
            "filename" : saved["filename"],
            "uploaded_at" : datetime.now(timezone.utc).isoformat(),
            "size_bytes" : saved["size_bytes"],
            "status" : "uploaded",
            "spatial": {
                "coordinate_system": "model_xy", # EOV később
                "background_mode" : "none",      # Map később
            },
            "summary" : summary
        }
        logger.info(
            "Model uploaded: model_id=%s filename=%s size=%d",
            saved["model_id"],
            saved["filename"],
            saved["size_bytes"]
        )
   
        return (
            network_state, 
            dbc.Alert(
                f"Uploaded {saved['filename']} successfully.",
                color="success",
                className="upload-alert",
            ),  # pyright: ignore[reportCallIssue]
            None, # invalidate previous hydraulic run
            None, # invalidate previous partition run
        )
            
    @app.callback(
        Output(ids.ACTIVE_MODEL_SUMMARY, "children"),
        Input(ids.NETWORK_STORE, "data"),
        Input(ids.URL, "pathname")
    )  
    def render_active_model_summary(network_state, pathname):  
        if pathname != "/network/load":
            raise PreventUpdate
        
        return render_model_summary(network_state)
    
    @app.callback(
        Output(ids.NETWORK_VIEW_STORE, "data"),
        Output(ids.LOAD_MODEL_STATUS, "children"),
        Input(ids.NETWORK_STORE, "data"),
        prevent_initial_call=True
    )
    def load_model_view(network_state):
        if not network_state:
            return None, None
            
        try:
            inp_path = resolve_uploaded_model(
            network_state["model_id"],
            network_state["filename"])
            model_data = read_water_network_model(inp_path)
            model_data["model_id"] = network_state["model_id"]
            model_data["filename"] = network_state["filename"]
        except Exception as exc:
            logger.exception(
                "Network view build failed: model_id=%s filename=%s",
                network_state.get("model_id", ""),
                network_state.get("filename", "")
            )
            return None, dbc.Alert(
                f"Model load failed: {exc}",
                color="danger",
                className="upload-alert",
                )  # pyright: ignore[reportCallIssue]
            
        return model_data, dbc.Alert(
                f"Loaded model data from {network_state['filename']}.",
                color="success",
                className="upload-alert",
                ) # pyright: ignore[reportCallIssue]
    
    @app.callback(
        Output(ids.NODE_COLOR_MIN, "value"),
        Output(ids.NODE_COLOR_MAX, "value"),
        Output(ids.NODE_COLOR_MIN, "disabled"),
        Output(ids.NODE_COLOR_MAX, "disabled"),
        Output(ids.LINK_COLOR_MIN, "value"),
        Output(ids.LINK_COLOR_MAX, "value"),
        Output(ids.LINK_COLOR_MIN, "disabled"),
        Output(ids.LINK_COLOR_MAX, "disabled"),
        Input(ids.NETWORK_VIEW_STORE, "data"),
        Input(ids.NODE_COLOR_BY, "value"),
        Input(ids.LINK_COLOR_BY, "value")
    )
    def sync_color_range(
        network_view_state,
        node_color_by,
        link_color_by
    ):
        if not network_view_state:
            return (
                None, None, True, True,
                None, None, True, True,
            )

        ranges = network_view_state.get("ranges", {})
        def _get_range(attribute):
            info = ranges.get(attribute, {})
            vmin = info.get("min")
            vmax = info.get("max")
            disabled = vmin is None or vmax is None

            return vmin, vmax, disabled, disabled
        
        node_values = _get_range(node_color_by)
        link_values = _get_range(link_color_by)
        
        if ctx.triggered_id == ids.NODE_COLOR_BY:
            return *node_values, no_update, no_update, no_update, no_update
        
        if ctx.triggered_id == ids.LINK_COLOR_BY:
            return no_update, no_update, no_update, no_update, *link_values
        
        return *node_values, *link_values
    
    
    @app.callback(
        Output(ids.NETWORK_GRAPH, "figure"),
        Input(ids.NETWORK_VIEW_STORE, "data"),
        Input(ids.NODE_COLOR_BY, "value"),
        Input(ids.LINK_COLOR_BY, "value"),
        Input(ids.NODE_COLOR_MIN, "value"),
        Input(ids.NODE_COLOR_MAX, "value"),
        Input(ids.LINK_COLOR_MIN, "value"),
        Input(ids.LINK_COLOR_MAX, "value")
    )
    def render_network_grap(
        network_view_state, 
        node_color_by, 
        link_color_by,
        node_cmin,
        node_cmax,
        link_cmin,
        link_cmax):
        #if not network_view_state:
        #    raise PreventUpdate
        
        return make_node_preview_figure(
            network_view_state, 
            node_color_by, 
            link_color_by,
            node_cmin=node_cmin,
            node_cmax=node_cmax,
            link_cmin=link_cmin,
            link_cmax=link_cmax)