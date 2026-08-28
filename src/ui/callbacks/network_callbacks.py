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
from src.services.inp_model_reader import read_model_summary, read_water_network_model
from src.ui.pages.network_load import render_model_summary
from src.visualisation.network_preview import make_node_preview_figure
from src.config import UPLOAD_ROOT


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
            return no_update, dbc.Alert(
                "Please upload an EPANET .inp file.",
                color="warning",
                className="upload-alert"
            ) # pyright: ignore[reportCallIssue]
        
        try:
            file_bytes = _decode_upload(contents)
            saved = _save_uploaded_file(filename, file_bytes)
        except Exception as exc:
                return no_update, dbc.Alert(
                    f"Upload failed: {exc}",
                    color="danger",
                    className="upload-alert",
                ) # pyright: ignore[reportCallIssue]
        
        
        summary = {}
        try:
            summary = read_model_summary(saved["path"])
        except Exception as e:
            return no_update, dbc.Alert(
            f"Model load failed: {e}",
            color="danger",
            className="upload-alert",
            ) # pyright: ignore[reportCallIssue]
        
        network_state = {
            "model_id" : saved["model_id"],
            "filename" : saved["filename"],
            "uploaded_at" : datetime.now(timezone.utc).isoformat(),
            "size_bytes" : saved["size_bytes"],
            "status" : "uploaded",
            "storage" : {
                "backend": "local",
                "path" : saved["path"]
            },
            "spatial": {
                "coordinate_system": "model_xy", # EOV később
                "background_mode" : "none",      # Map később
            },
            "summary" : summary
        }
   
        return network_state, dbc.Alert(
                f"Uploaded {saved['filename']} successfully.",
                color="success",
                className="upload-alert",
            )  # pyright: ignore[reportCallIssue]
      
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
            raise PreventUpdate
            
        inp_path = network_state["storage"]["path"]
        try:
            model_data = read_water_network_model(inp_path)
        except Exception as e:
            return no_update, dbc.Alert(
            f"Model load failed: {e}",
            color="danger",
            className="upload-alert",
        )  # pyright: ignore[reportCallIssue]
            
        return model_data, dbc.Alert(
            f"Loaded model data from {network_state['filename']}.",
            color="success",
            className="upload-alert",
        ) # pyright: ignore[reportCallIssue]
    
    
    @app.callback(
        Output(ids.NETWORK_GRAPH, "figure"),
        Input(ids.NETWORK_VIEW_STORE, "data"),
        Input(ids.NODE_COLOR_BY, "value"),
        Input(ids.LINK_COLOR_BY, "value"),
    )
    def render_network_grap(network_view_state, node_color_by, link_color_by):
        if not network_view_state:
            raise PreventUpdate
        
        return make_node_preview_figure(network_view_state, node_color_by, link_color_by)