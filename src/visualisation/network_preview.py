from __future__ import annotations

from typing import Dict, Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale, qualitative

from src.results.hydraulic import open_eps_hydraulic_results
from src.visualisation.common import (
    append_line_segment,
    apply_network_layout,
    make_empty_network_figure,
    model_ids_are_compatible,
    node_positions,
    make_discrete_colorscale,
    normalize_display_value
)


N_LINK_BINS = 5

LINK_BIN_COLORS = sample_colorscale(
    "Turbo",
    np.linspace(0.05, 0.95, N_LINK_BINS),
)

LINK_COLORSCALE = make_discrete_colorscale(LINK_BIN_COLORS) # type: ignore

_ATTRIBUTE_LABELS = {
    "elevation": "Elevation",
    "demand": "Demand",
    "length": "Length",
    "diameter": "Diameter",
    "roughness": "Roughness",
    "pressure": "Pressure head",
    "head": "Hydraulic head",
    "flowrate": "Flow rate",
    "velocity": "Velocity",
    "headloss": "Head loss",
}

_DISPLAY_UNITS = {
    "m^3/h": "m³/h",
    "m3/h": "m³/h",
    "m^3/s": "m³/s",
    "m3/s": "m³/s",
}


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

def _format_colorbar_title(
    attribute: str,
    unit: str | None,
) -> str:
    label = _ATTRIBUTE_LABELS.get(
        attribute,
        attribute.replace("_", " ").title(),
    )

    if not unit or unit.lower() == "none":
        return label

    display_unit = _DISPLAY_UNITS.get(
        unit,
        unit,
    )

    return f"{label} [{display_unit}]"

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
    link_unit: str | None,
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
                "title": _format_colorbar_title(
                    link_attribute,
                    link_unit,
                ),
                "x": 1.02,
                "y": 0.24,
                "len": 0.38,
                "thickness": 12,
            },
        },
        hoverinfo="skip",
        showlegend=False,
    )

def _validate_normalize_color_range(
    cmin: float | None,  cmax: float | None
    ) -> tuple[float | None, float |None]:
    if cmin is None or cmax is None:
        return cmin, cmax

    if cmin > cmax:
        raise ValueError

    if np.isclose(cmin, cmax):
        pad = max(abs(cmin) * 1e-6, 1e-9)
        return cmin - pad, cmax + pad


    return cmin, cmax


def _make_node_trace(
    *,
    nodes: Dict[str, Any],
    node_values: pd.Series,
    node_attribute: str,
    node_unit: str | None,
    cmin: float | None,
    cmax: float | None,
    marker_size: float,
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

        if node_attribute == "none":
            hover_text.append(
                f"<b>{node_id}</b><br>"
                f"Type: {node_type}<br>"
            )
        else:
            hover_text.append(
                f"<b>{node_id}</b><br>"
                f"Type: {node_type}<br>"
                f"{node_attribute}: {_format_value(value)}"
            )

    if node_attribute == "none":
        marker = {
            "size" : marker_size,
            "opacity" : 0.9,
            "color" : "#104dc7",
            "line": {"width" : 0.5, "color" : "white"}
        }
        
    else:
        marker={
            "size" : marker_size,
            "opacity" : 0.9,
            "color" : plot_color,
            "colorscale" : "Viridis",
            "cmin" : cmin,
            "cmax" : cmax,
            "showscale": True,
            "colorbar" : {
                "title": _format_colorbar_title(
                    node_attribute,
                    node_unit,
                ),
                "x"     : 1.02,
                "y"     : 0.76,
                "len"   : 0.38,
                "thickness" : 12
            },
            "line" : {"width": 0.5, "color": "white"}
        }

    return go.Scattergl(
        x=plot_x,
        y=plot_y,
        mode="markers",
        marker=marker,
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
    n_bins: int,
    line_width_scale: float
) -> list[go.Scatter | go.Scattergl]:
    node_x = nodes.get("x", [])
    node_y = nodes.get("y", [])
    
    link_ids = links.get("id", [])
    start_indices = links.get("start_index", [])
    end_indices = links.get("end_index", [])
    
    missing_x = []
    missing_y = []
    
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
        
        if link_values is None or link_id not in link_values.index:
            missing_x.extend([x0, x1, None])
            missing_y.extend([y0, y1, None])
            continue
        
        value = link_values[link_id]
    
        if pd.isna(value):
            missing_x.extend([x0, x1, None])
            missing_y.extend([y0, y1, None])
            continue
        
        if bin_edges is None:
            bin_id = 0
        else:
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
                    "width": 1.4 * line_width_scale,
                    "color": LINK_BIN_COLORS[i]
                },
                hoverinfo="skip",
                name=f"{link_attribute} bin {i + 1}",
                showlegend=False,
            )
        )
        
    if missing_x:
        traces.insert(
            0,
            go.Scattergl(
                x=missing_x,
                y=missing_y,
                mode="lines",
                line={
                    "width": 1.0 * line_width_scale,
                    "color" : "#343841"
                },
                hoverinfo="skip",
                showlegend=False
            )
        )

    return traces        


def _make_attribute_network_figure(
    *,
    network_view_state: dict[str, Any],
    node_values: pd.Series,
    link_values: pd.Series | None,
    node_attribute: str,
    link_attribute: str,
    node_unit: str | None,
    link_unit: str | None,
    node_cmin: float | None,
    node_cmax: float | None,
    link_cmin: float | None,
    link_cmax: float | None,
    uirevision: str,
    title: dict[str, Any] | None = None,
    line_width_scale: float = 1.0,
    marker_size: float = 5.0,
    hide_nodes: bool = False,
) -> go.Figure:

    line_width_scale = normalize_display_value(
        line_width_scale,
        default=1.0,
        minimum=0.25,
        maximum=4.0,
    )

    marker_size = normalize_display_value(
        marker_size,
        default=5.0,
        minimum=1.0,
        maximum=20.0,
    )

    nodes = network_view_state.get("nodes", {})
    links = network_view_state.get("links", {})

    positions = node_positions(nodes)

    if not nodes.get("x", []) or not nodes.get("y", []):
        return make_empty_network_figure(
            "The loaded model has no node coordinates."
        )

    if not positions:
        return make_empty_network_figure(
            "The loaded model has no valid node coordinates."
        )

    if not hide_nodes:
        try:
            node_cmin, node_cmax = (
                _validate_normalize_color_range(
                    node_cmin,
                    node_cmax,
                )
            )
        except ValueError:
            return make_empty_network_figure(
                "Node color minimum must not be greater "
                "than maximum."
            )

    try:
        link_cmin, link_cmax = (
            _validate_normalize_color_range(
                link_cmin,
                link_cmax,
            )
        )
    except ValueError:
        return make_empty_network_figure(
            "Link color minimum must not be greater "
            "than maximum."
        )

    link_bin_edges = _make_link_bin_edges(
        (link_cmin, link_cmax),
        N_LINK_BINS,
    )

    link_traces = _make_link_traces(
        nodes=nodes,
        links=links,
        link_values=link_values,
        link_attribute=link_attribute,
        bin_edges=link_bin_edges,
        n_bins=N_LINK_BINS,
        line_width_scale=line_width_scale
    )

    link_colorbar_trace = _make_link_colorbar_trace(
        link_attribute=link_attribute,
        link_unit=link_unit,
        cmin=link_cmin,
        cmax=link_cmax,
    )

    traces: list[go.Scatter | go.Scattergl] = [*link_traces]
    if not hide_nodes:
        node_trace = _make_node_trace(
                nodes=nodes,
                node_values=node_values,
                node_attribute=node_attribute,
                node_unit=node_unit,
                cmin=node_cmin,
                cmax=node_cmax,
                marker_size=marker_size
            )

        traces.append(node_trace)


    if link_colorbar_trace is not None:
        traces.append(link_colorbar_trace)

    figure = go.Figure(data=traces)

    return apply_network_layout(
        figure,
        uirevision=uirevision,
        title=title,
        )

def make_node_preview_figure(
    network_view_state: dict[str, Any],
    node_color_by: str = "none",
    link_color_by: str = "none",
    node_cmin: float | None = None,
    node_cmax: float | None = None,
    link_cmin: float | None = None,
    link_cmax: float | None = None,
    line_width_scale: float = 1.0,
    marker_size: float = 5.0,
    hide_nodes: bool = False,
) -> go.Figure:
    if not network_view_state:
        return make_empty_network_figure()

    nodes = network_view_state.get("nodes", {})
    links = network_view_state.get("links", {})
    ranges = network_view_state.get("ranges", {})

    node_ids = nodes.get("id", [])
    link_ids = links.get("id", [])

    node_unit = ranges.get(node_color_by, {}).get("unit")
    link_unit = ranges.get(link_color_by, {}).get("unit")

    node_values = pd.Series(
        data=nodes.get(node_color_by),
        index=node_ids,
    )

    link_values = pd.Series(
        data=links.get(link_color_by),
        index=link_ids,
    )

    return _make_attribute_network_figure(
        network_view_state=network_view_state,
        node_values=node_values,
        link_values=link_values,
        node_attribute=node_color_by,
        link_attribute=link_color_by,
        node_unit=node_unit,
        link_unit=link_unit,
        node_cmin=node_cmin,
        node_cmax=node_cmax,
        link_cmin=link_cmin,
        link_cmax=link_cmax,
        line_width_scale = line_width_scale,
        marker_size = marker_size,
        hide_nodes = hide_nodes,
        uirevision=str(
            network_view_state.get(
                "model_id",
                "model-view",
            )
        ),
    )



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
    link_cmax: float | None = None,
    line_width_scale: float = 1.0,
    marker_size: float = 5.0,
    hide_nodes: bool = False,
) -> go.Figure:
    
    if not run_state:
        return make_empty_network_figure(
            "Run a hydraulic simulation to view animated network results."
        )
        
    if not network_view_state:
        return make_empty_network_figure(
            "Build the network preview before plotting hydraulic results."
        )
    
    if not model_ids_are_compatible(
        run_state,
        network_view_state,
    ):
        return make_empty_network_figure(
            "Hydraulic results belong to a different network model."
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
    
      
    nodes = network_view_state.get("nodes", {})
    links = network_view_state.get("links", {})
    ranges = run_state.get("ranges", {})

    node_ids = nodes.get("id", [])
    link_ids = links.get("id", [])

    node_unit = ranges.get(node_result, {}).get("unit")
    link_unit = ranges.get(link_result, {}).get("unit")

    if time_index is None:
        time_index = 0

    time_index = int(time_index)
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
    
    title_layout = {
        "text": title,
        "x": 0.02,
        "y": 0.9,
        "xanchor": "left",
        "font": {
            "size": 14,
        },
    }

    return _make_attribute_network_figure(
        network_view_state=network_view_state,
        node_values=node_values,
        link_values=link_values,
        node_attribute=node_result,
        link_attribute=link_result,
        node_unit=node_unit,
        link_unit=link_unit,
        node_cmin=node_cmin,
        node_cmax=node_cmax,
        link_cmin=link_cmin,
        link_cmax=link_cmax,
        line_width_scale = line_width_scale,
        marker_size = marker_size,
        hide_nodes = hide_nodes,
        uirevision=str(
            run_state.get(
                "run_id",
                "hydraulic-run",
            )
        ),
        title=title_layout,
    )
    
    
def make_partitioned_network_figure(
    *,
    network_view_state: Dict[str, Any],
    partition_state: Dict[str, Any],
    selected_communities: list[str],
    show_boundary_links: bool = False,
    line_width_scale: float = 1.0,
    marker_size: float = 5.0,
    hide_nodes: bool = False,
) -> go.Figure:

    line_width_scale = normalize_display_value(
        line_width_scale,
        default=1.0,
        minimum=0.25,
        maximum=4.0,
    )

    marker_size = normalize_display_value(
        marker_size,
        default=5.0,
        minimum=1.0,
        maximum=20.0,
    )

    if not partition_state:
        return make_empty_network_figure(
            "Run optimization to view network partitions."
        )

    if not network_view_state:
        return make_empty_network_figure(
            "Build the network preview before plotting "
            "partitioning results."
        )

    if not model_ids_are_compatible(
        partition_state,
        network_view_state,
    ):
        return make_empty_network_figure(
            "Partitioning results belong to a different "
            "network model."
        )

    node_community = partition_state.get(
        "node_community"
    )

    if not node_community:
        return make_empty_network_figure(
            "Partitioning result has no communities."
        )

    nodes = network_view_state.get("nodes", {})
    links = network_view_state.get("links", {})

    node_ids = [
        str(value)
        for value in nodes.get("id", [])
    ]
    start_nodes = [
        str(value)
        for value in links.get(
            "start_node",
            [],
        )
    ]
    end_nodes = [
        str(value)
        for value in links.get(
            "end_node",
            [],
        )
    ]

    # An empty selection means that every community is shown.
    selected = {
        str(community_id)
        for community_id in (
            selected_communities or []
        )
    }

    def _is_visible(node_id: str) -> bool:
        community = node_community.get(node_id)

        if community is None:
            return False

        return (
            not selected
            or str(community) in selected
        )

    positions = node_positions(nodes)

    visible_node_ids = [
        node_id
        for node_id in node_ids
        if (
            node_id in positions
            and _is_visible(node_id)
        )
    ]

    if not visible_node_ids:
        return make_empty_network_figure(
            "No nodes belong to the selected communities."
        )

    visible_nodes = set(visible_node_ids)

    link_coordinates: dict[
        str,
        list[float | None],
    ] = {
        "x": [],
        "y": [],
    }
    boundary_coordinates: dict[
        str,
        list[float | None],
    ] = {
        "x": [],
        "y": [],
    }

    for start_node, end_node in zip(
        start_nodes,
        end_nodes,
    ):
        if (
            start_node not in visible_nodes
            or end_node not in visible_nodes
        ):
            continue

        start_position = positions.get(start_node)
        end_position = positions.get(end_node)

        if (
            start_position is None
            or end_position is None
        ):
            continue

        start_community = node_community.get(
            start_node
        )
        end_community = node_community.get(
            end_node
        )

        is_boundary = (
            start_community is not None
            and end_community is not None
            and start_community
            != end_community
        )

        target_coordinates = (
            boundary_coordinates
            if show_boundary_links and is_boundary
            else link_coordinates
        )

        append_line_segment(
            target_coordinates,
            start_position,
            end_position,
        )

    link_trace = go.Scattergl(
        x=link_coordinates["x"],
        y=link_coordinates["y"],
        mode="lines",
        line={
            "width": 1.0 * line_width_scale,
            "color": LINK_BIN_COLORS[0],
        },
        hoverinfo="skip",
        showlegend=False,
    )

    boundary_trace = go.Scattergl(
        x=boundary_coordinates["x"],
        y=boundary_coordinates["y"],
        mode="lines",
        line={
            "width": 3.0 * line_width_scale,
            "color": "red",
        },
        hoverinfo="skip",
        name="Boundary links",
        showlegend=(
            show_boundary_links
            and bool(boundary_coordinates["x"])
        ),
    )

    community_ids = sorted(
        set(node_community.values())
    )

    community_to_color_index = {
        community_id: index
        for index, community_id
        in enumerate(community_ids)
    }

    node_colors = [
        community_to_color_index[
            node_community[node_id]
        ]
        for node_id in visible_node_ids
    ]

    node_hover = [
        (
            f"<b>{node_id}</b>"
            f"<br>Community: "
            f"{node_community[node_id]}"
        )
        for node_id in visible_node_ids
    ]

    palette = qualitative.Plotly
    colorscale = []
    n_colors = len(community_ids)

    for index in range(n_colors):
        color = palette[
            index % len(palette)
        ]

        lower = index / n_colors
        upper = (index + 1) / n_colors

        colorscale.extend(
            [
                [lower, color],
                [upper, color],
            ]
        )

    node_trace = go.Scattergl(
        x=[
            positions[node_id][0]
            for node_id in visible_node_ids
        ],
        y=[
            positions[node_id][1]
            for node_id in visible_node_ids
        ],
        mode="markers",
        customdata=visible_node_ids,
        hovertext=node_hover,
        hoverinfo="text",
        marker={
            "size": marker_size,
            "color": node_colors,
            "colorscale": colorscale,
            "cmin": -0.5,
            "cmax": n_colors - 0.5,
            "showscale": True,
            "colorbar": {
                "title": "Community",
                "x": 1.02,
                "y": 0.24,
                "len": 0.38,
                "thickness": 12,
                "tickmode": "array",
                "tickvals": list(
                    range(n_colors)
                ),
                "ticktext": [
                    str(community_id)
                    for community_id
                    in community_ids
                ],
            },
        },
        showlegend=False,
    )

    traces = [link_trace, boundary_trace]
    if not hide_nodes:
        traces.append(node_trace)

    figure = go.Figure(
        data=traces
    )

    return apply_network_layout(
        figure,
        uirevision=str(
            partition_state.get(
                "run_id",
                "partition-run",
            )
        ),
        legend={
            "x": 0.05,
            "y": 0.94,
            "xanchor": "left",
            "yanchor": "top",
        },
    )