from __future__ import annotations
from dash import Input, Output, State, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from src.ui import ids
from src.ui.pages.components import render_active_model_summary
from src.ui.pages.network_partitioning import render_success_alert
from src.services.model_storage import resolve_uploaded_model
from src.services.partition_runner import call_staci_split_service
from src.visualisation.network_preview import make_partitioned_network_figure

import logging
logger = logging.getLogger(__name__)

def register_partitioning_callbacks(app):
    
    @app.callback(
        Output(ids.PART_ACTIVE_MODEL_SUMMARY, "children"),
        Output(ids.PART_RUN_BUTTON, "disabled"),
        Input(ids.NETWORK_STORE, "data")
    )
    def sync_active_model(network_state):
        if not network_state:
            return render_active_model_summary(network_state), True
        
        return render_active_model_summary(network_state), False


    @app.callback(
        Output(ids.PART_RUN_STORE, "data"),
        Output(ids.PART_RUN_STATUS, "children"),
        Input(ids.PART_RUN_BUTTON, "n_clicks"),
        State(ids.NETWORK_STORE, "data"),
        State(ids.PART_NCOMM, "value"),
        State(ids.PART_OBJECTIVE, "value"),
        State(ids.PART_WEIGHT_TYPE, "value"),
        State(ids.PART_WEIGHT_MOD, "value"),
        State(ids.PART_POPSIZE, "value"),
        State(ids.PART_NGEN, "value"),
        State(ids.PART_PMUT, "value"),
        State(ids.PART_PCROSS, "value"),
        State(ids.PART_SEED, "value")
    )
    def run_partitioning(
        n_clicks,
        network_state,
        n_comm,
        obj_type,
        weight_type,
        weight_type_mod,
        popsize,
        ngen,
        pmut,
        pcross,
        seed
    ):
        if not n_clicks:
            raise PreventUpdate
        
        if not network_state:
            return no_update, dbc.Alert(
                "No active INP file. Upload a model first",
                color="warning",
                className="upload-alert"
            ) # pyright: ignore[reportCallIssue]
        
        try:
            inp_path = resolve_uploaded_model(
                network_state["model_id"],
                network_state["filename"]
            )
            
            optimizer_settings = {
                "n_comm" : n_comm,
                "obj_type" : obj_type,
                "weight_type" : weight_type,
                "weight_type_mod" : weight_type_mod,
                "popsize" : popsize,
                "ngen" : ngen,
                "pmut" : pmut,
                "pcross" : pcross
            }
            
            logger.info(
                "Network partitioning started: model_id=%s n_comm=%d objs_type=%s seed=%d",
                network_state.get("model_id", ""),
                n_comm,
                obj_type,
                seed
            )
            
            partition_state = call_staci_split_service(
                inp_path,
                model_id=network_state.get("model_id"),
                optimizer_settings=optimizer_settings,
                seed=seed
            )
            
            logger.info(
                "Network partitioning finished: run_id=%s model_id=%s n_comm=%d objs_type=%s seed=%d",
                partition_state.get("run_id", ""),
                partition_state.get("model_id", ""),
                n_comm,
                obj_type,
                seed
            )

        except Exception as exc:
            logger.exception(
                "Network partitioning failed: model_id=%s",
                network_state["model_id"]
            )
            return None, dbc.Alert(
                f"Network partition failed: {exc}",
                color="danger",
                className="upload-alert"
            ) # pyright: ignore[reportCallIssue]
            
        return partition_state, render_success_alert(partition_state)
    

    @app.callback(
        Output(ids.PART_COMMUNITY_FILTER, "options"),
        Output(ids.PART_COMMUNITY_FILTER, "value"),
        Input(ids.PART_RUN_STORE, "data")
    )    
    def update_plot_toolbar(
        partition_state
    ):
        if not partition_state:
            return no_update
        
        node_community = partition_state.get("node_community")
        
        if not node_community:
            return [], []
        
        options = [
            {
                "label": f"Community {community_id}",
                "value": community_id,
            }
            for community_id in sorted(
                set(node_community.values())
            )
        ]
        
        return options, []
    
    
    @app.callback(
        Output(ids.PART_NETWORK_GRAPH, "figure"),
        Input(ids.PART_RUN_STORE, "data"),
        Input(ids.PART_COMMUNITY_FILTER, "value"),
        Input(ids.PART_SHOW_BOUNDARY_LINKS, "value"),
        State(ids.NETWORK_VIEW_STORE, "data")
    )
    def render_partitioned_network_graph(
        partition_stace,
        selected_communities,
        show_boundary_links,
        network_view_state,
    ):
        return make_partitioned_network_figure(
            network_view_state=network_view_state,
            partition_state=partition_stace,
            selected_communities=selected_communities,
            show_boundary_links=show_boundary_links
        )    
    