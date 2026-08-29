from __future__ import annotations
from typing import Dict, Any
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from plotly.colors import sample_colorscale
from src.results.hydraulic import open_eps_hydraulic_results

FIG_LAYOUT = {
    "template"  : "plotly_white",
    "height"    : 470,
    "margin"    : {"l": 10, "r": 10, "t": 10, "b": 10},
    "xaxis"     : {"visible": False, "showgrid": False, "zeroline": False, "scaleanchor": "y", "scaleratio": 1},
    "yaxis"     : {"visible": False, "showgrid": False, "zeroline": False}
}

N_LINK_BINS = 5

LINK_BIN_COLORS = sample_colorscale(
    "Turbo",
    np.linspace(0.05, 0.95, N_LINK_BINS),
)

def _make_discrete_colorscale(
    colors
) -> list[list[float | str]]:
    n = len(colors)
    scale = []

    for i, color in enumerate(colors):
        lower = i / n
        upper = (i + 1) / n

        scale.append([lower, color])
        scale.append([upper, color])

    return scale

LINK_COLORSCALE = _make_discrete_colorscale(LINK_BIN_COLORS)

# ---- Format Helpers ----
def _format_time_seconds(value) -> str:
    try:
        seconds = int(float(value))
    except (TypeError, ValueError):
        return str(value)

    hours = seconds / 3600.0

    if abs(hours - round(hours)) < 1e-9:
        return f"{int(round(hours))} h"

    return f"{hours:.2f} h"

def _format_value(value) -> str:
    if value is None:
        return "—"
    try:
        if np.isnan(value):
            return "—"
    except TypeError:
        pass

    try:
        return f"{float(value):.3g}"
    except (TypeError, ValueError):
        return str(value)

def _make_link_bin_edges(
    data_range: tuple[float | None, float | None],
    n_bins: int,
) -> np.ndarray | None:
    vmin, vmax = data_range

    if vmin is None or vmax is None:
        return None

    if not np.isfinite(vmin) or not np.isfinite(vmax):
        return None

    if vmin >= vmax:
        return None

    return np.linspace(vmin, vmax, n_bins + 1)

def _make_link_colorbar_trace(
    *,
    link_attribute: str,
    cmin: float | None,
    cmax: float | None
) -> go.Scatter | None:
    if cmin is None or cmax is None:
        return None

    if not np.isfinite(cmin) or not np.isfinite(cmax):
        return None

    if cmin >= cmax:
        return None
    
    return go.Scatter(
        x=[None, None],
        y=[None, None],
        mode="markers",
        marker={
            "color": [cmin, cmax],
            "cmin": cmin,
            "cmax": cmax,
            "colorscale": LINK_COLORSCALE,
            "showscale": True,
            "colorbar": {
                "title": link_attribute,
                "x": 1.02,
                "y": 0.24,
                "len": 0.38,
                "thickness": 12,
            },
        },
        hoverinfo="skip",
        showlegend=False,
    )

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

def _make_node_trace(
    *,
    nodes: Dict[str, Any],
    node_values: pd.Series,
    node_attribute: str,
    cmin: float | None,
    cmax: float | None
) -> go.Scattergl:
    node_ids = nodes.get("id", [])
    node_types = nodes.get("type", [])
    node_x = nodes.get("x", [])
    node_y = nodes.get("y", [])
    
    plot_x, plot_y, plot_color, hover_text = [], [], [], []
    for i, node_id in enumerate(node_ids):
        if i >= len(node_x) or i >= len(node_y):
            continue
        
        x = node_x[i]
        y = node_y[i]
        
        if x is None or y is None:
            continue
        value = node_values[node_id] if node_id in node_values.index else np.nan
        node_type = node_types[i] if i < len(node_types) else "node"
        
        plot_x.append(x)
        plot_y.append(y)
        plot_color.append(value)

        hover_text.append(
            f"<b>{node_id}</b><br>"
            f"Type: {node_type}<br>"
            f"{node_attribute}: {_format_value(value)}"
        )

    return go.Scattergl(
        x=plot_x,
        y=plot_y,
        mode="markers",
        marker={
            "size" : 5,
            "opacity" : 0.9,
            "color" : plot_color,
            "colorscale" : "Viridis",
            "cmin" : cmin,
            "cmax" : cmax,
            "showscale": True,
            "colorbar" : {
                "title" : node_attribute,
                "x"     : 1.02,
                "y"     : 0.76,
                "len"   : 0.38,
                "thickness" : 12
            },
            "line" : {"width": 0.5, "color": "white"}
        },
        text=hover_text,
        hoverinfo="text",
        name="Nodes",
        showlegend=False
    )

def _make_link_traces(
    *,
    nodes: Dict[str, Any],
    links: Dict[str, Any],
    link_values: pd.Series | None,
    link_attribute: str,
    bin_edges: np.ndarray | None,
    n_bins: int
) -> list[go.Scatter]:
    node_x = nodes.get("x", [])
    node_y = nodes.get("y", [])
    
    link_ids = links.get("id", [])
    start_indices = links.get("start_index", [])
    end_indices = links.get("end_index", [])
    
    bin_x = [[] for _ in range(n_bins)]
    bin_y = [[] for _ in range(n_bins)]

    for i, link_id in enumerate(link_ids):
        if i >= len(start_indices) or i >= len(end_indices):
            continue
        
        start_idx = start_indices[i]
        end_idx   = end_indices[i]
        
        if start_idx >= len(node_x) or end_idx >= len(node_x):
            continue
        
        x0 = node_x[start_idx]
        y0 = node_y[start_idx]
        x1 = node_x[end_idx]
        y1 = node_y[end_idx]
        
        if None in (x0, y0, x1, y1):
            continue
        
        bin_id = 0
        if link_values is not None and link_id in link_values.index:
            value = link_values[link_id]

            if pd.notna(value) and bin_edges is not None:
                bin_id = int(
                    np.searchsorted(
                        bin_edges,
                        float(value),
                        side="right",
                    )
                    - 1
                )
                bin_id = max(0, min(n_bins - 1, bin_id))

        bin_x[bin_id].extend([x0, x1, None])
        bin_y[bin_id].extend([y0, y1, None])
        
    traces = []
        
    for i in range(n_bins):
        traces.append(
            go.Scatter(
                x=bin_x[i],
                y=bin_y[i],
                mode="lines",
                line={
                    "width": 1.4,
                    "color": LINK_BIN_COLORS[i]
                },
                hoverinfo="skip",
                name=f"{link_attribute} bin {i + 1}",
                showlegend=False,
            )
        )

    return traces        
                

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
        "opacity": 0.9,
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



def make_hydraulic_timestep_figure(
    *,
    network_view_state: Dict[str, Any],
    run_state: Dict[str, Any],
    time_index: int | None,
    node_result: str = "pressure",
    link_result: str = "flowrate",
    node_cmin: float | None = None,
    node_cmax: float | None = None,
    link_cmin: float | None = None,
    link_cmax: float | None = None
) -> go.Figure:
    
    if not run_state:
        return make_empty_network_figure(
            "Run a hydraulic simulation to view network results."
        )
        
    if not network_view_state:
        return make_empty_network_figure(
            "Build the network preview before plotting hydraulic results."
        )
    
    results = open_eps_hydraulic_results(run_state)
    
    if results.n_steps == 0:
        return make_empty_network_figure(
            "The hydraulic run has no time steps."
        )
        
    if node_result not in results.node_attributes:
        return make_empty_network_figure(
            f"Node result '{node_result}' is not available for this run."
        )
        
    if link_result not in results.link_attributes:
        return make_empty_network_figure(
            f"Link result '{link_result}' is not available for this run."
        )
    
    if (
        node_cmin is not None
        and node_cmax is not None
        and node_cmin >= node_cmax):
        return make_empty_network_figure(
            "Node color minimum must be smaller than maximum."
        )

    if (
        link_cmin is not None
        and link_cmax is not None
        and link_cmin >= link_cmax):
        return make_empty_network_figure(
            "Link color minimum must be smaller than maximum."
        )
      
    nodes = network_view_state.get("nodes", {})
    links = network_view_state.get("links", {})

    node_ids = nodes.get("id", [])
    link_ids = links.get("id", [])
    
    if time_index is None:
        time_index = 0

    time_index = max(
        0,
        min(int(time_index), results.n_steps - 1),
    )

    time_value = results.times[time_index]
    
    node_values = results.node_frame(
        attribute=node_result,
        time_index=time_index
    ).reindex(node_ids)
    
    link_values = results.link_frame(
        attribute=link_result,
        time_index=time_index
    ).reindex(link_ids)
    
    converged = results.frame_converged(time_index)
    title = (
        f"{node_result} / {link_result}"
        f" · {_format_time_seconds(time_value)}"
    )

    if not converged:
        title += " · ⚠ not converged"
    
    node_trace = _make_node_trace(
        nodes=nodes,
        node_values=node_values,
        node_attribute=node_result,
        cmin=node_cmin,
        cmax=node_cmax
    )
    
    link_bin_edges = _make_link_bin_edges(
        (link_cmin, link_cmax),
        N_LINK_BINS
    )
    
    link_traces = _make_link_traces(
        nodes=nodes,
        links=links,
        link_values=link_values,
        link_attribute=link_result,
        bin_edges=link_bin_edges,
        n_bins=N_LINK_BINS,
    )
    
    link_colorbar_trace = _make_link_colorbar_trace(
        link_attribute=link_result,
        cmin=link_cmin,
        cmax=link_cmax
    )
    
    traces = [*link_traces, node_trace]
    if link_colorbar_trace is not None:
        traces.append(link_colorbar_trace)
    
    fig = go.Figure(data=traces)
    
    fig.update_layout(**FIG_LAYOUT,
        uirevision=run_state.get(
            "run_id",
            "hydraulic-run",
        ),  # Fix view between updates
        title = {
            "text"      : title,
            "x"         : 0.02,
            "y"         : 0.9,
            "xanchor"   : "left",
            "font"      : {"size": 14}
        })
    
    return fig
    