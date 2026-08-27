from __future__ import annotations
from typing import Dict, Any
import plotly.graph_objects as go

FIG_LAYOUT = {
    "template"  : "plotly_white",
    "height"    : 470,
    "margin"    : {"l": 10, "r": 10, "t": 10, "b": 10},
    "xaxis"     : {"visible": False, "scaleanchor": "y", "scaleratio": 1},
    "yaxis"     : {"visible": False}
}

def make_empty_network_figure(
    message: str = "Upload a model to view the network preview."):
    fig = go.Figure()
    
    fig.update_layout(
        **FIG_LAYOUT,
          annotations=[
              {
                "text" : message,
                "xref" : "paper",
                "yref" : "paper",
                "x"    : 0.5,
                "y"    : 0.5,
                "showarrow" : False,
                "font" : {"size": 15, "color": "#6b7280"}
              }
          ]
        )
    
    return fig


def make_node_preview_figure(
    network_view_state: Dict[str, Any],
    node_color_by: str = "none", link_color_by: str = "none"
):
    # network-view-state---> model-data rename later
    
    nodes = network_view_state.get("nodes", {})
    x = nodes.get("x", [])
    y = nodes.get("y", [])
    
    node_id = nodes.get("id", [])
    node_type = nodes.get("type", [])
    elevation = nodes.get("elevation", [])
    base_demand = nodes.get("base_demand", [])
    
    if not x or not y:
        return make_empty_network_figure("The loaded model has no node coordinates.")
    
    valid_idx = [
        i for i, (xi, yi) in enumerate(zip(x, y))
        if xi is not None and yi is not None
    ]
    
    if not valid_idx:
        return make_empty_network_figure("The loaded model has no valid node coordinates.")
    
    plot_x = [x[i] for i in valid_idx]
    plot_y = [y[i] for i in valid_idx]
    plot_id = [node_id[i] for i in valid_idx]
    plot_type = [node_type[i] for i in valid_idx]
    plot_elevation = [elevation[i] for i in valid_idx]
    plot_demand = [base_demand[i] for i in valid_idx]
    
    hover_text = [
        (
            f"<b>{plot_id[i]}</b><br>"
            f"Type: {plot_type[i]}<br>"
            f"Elevation: {plot_elevation[i]}<br>"
            f"Base demand: {plot_demand[i]}"
        )
        for i in range(len(plot_id))
    ]
    
    marker = {
        "size": 5,
        "opacity": 0.85,
        "line": {"width": 0.5, "color": "white"},
    }
    
    # TODO: node type!
    if node_color_by == "elevation":
        marker["color"] = plot_elevation
        marker["colorscale"] = "Viridis"
        marker["showscale"] = True
        marker["colorbar"] = {"title": "Elevation"}
    elif node_color_by == "demand":
        marker["color"] = plot_demand
        marker["colorscale"] = "Blues"
        marker["showscale"] = True
        marker["colorbar"] = {"title": "Demand"}
    else:
        marker["color"] = "#137fc4"
        
    
    # TODO: add link color support
    links = network_view_state.get("links", {})

    link_x = []
    link_y = []

    start_indices = links.get("start_index", [])
    end_indices = links.get("end_index", [])

    for start_idx, end_idx in zip(start_indices, end_indices):
        x0 = x[start_idx]
        y0 = y[start_idx]
        x1 = x[end_idx]
        y1 = y[end_idx]

        if None in (x0, y0, x1, y1):
            continue

        link_x.extend([x0, x1, None])
        link_y.extend([y0, y1, None])
        
        
    # ---  Drawing ----
    fig = go.Figure()
    if link_x and link_y:
        fig.add_trace(
            go.Scatter(
                x=link_x,
                y=link_y,
                mode="lines",
                line={
                    "width": 1,
                    "color": "rgba(36, 99, 140, 0.35)",
                },
                hoverinfo="skip",
                name="Links",
            )
        )
        
    fig.add_trace(
        go.Scatter(
            x=plot_x,
            y=plot_y,
            mode="markers",
            marker=marker,
            text=hover_text,
            hoverinfo="text",
            name="Nodes",
        )
    )
    
    fig.update_layout(**FIG_LAYOUT)
    
    return fig
    