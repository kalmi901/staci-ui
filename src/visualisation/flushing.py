from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal

import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from src.visualisation.network_preview import (
    FIG_LAYOUT,
    make_empty_network_figure,
)


MapMode = Literal["coverage", "velocity"]

_COVERAGE_STYLES = {
    "No scenario data": {
        "color": "#cbd5e1",
        "width": 0.7,
    },
    "Below threshold": {
        "color": "#94a3b8",
        "width": 0.9,
    },
    "Above in baseline": {
        "color": "#2563eb",
        "width": 1.8,
    },
    "Newly above threshold": {
        "color": "#14b8a6",
        "width": 2.4,
    },
}

_VELOCITY_COLORS = sample_colorscale(
    "Turbo",
    [0.05, 0.275, 0.5, 0.725, 0.95],
)


def _node_positions(
    nodes: dict[str, Any],
) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}

    for node_id, x, y in zip(
        nodes.get("id", []),
        nodes.get("x", []),
        nodes.get("y", []),
    ):
        if x is None or y is None:
            continue

        positions[str(node_id)] = (
            float(x),
            float(y),
        )

    return positions


def _append_segment(
    group: dict[str, list[float | None]],
    start: tuple[float, float],
    end: tuple[float, float],
) -> None:
    group["x"].extend(
        [start[0], end[0], None]
    )
    group["y"].extend(
        [start[1], end[1], None]
    )


def _coverage_group(
    pipe: dict[str, Any] | None,
) -> str:
    if pipe is None:
        return "No scenario data"

    if not pipe.get("above_threshold"):
        return "Below threshold"

    if pipe.get("newly_above_threshold"):
        return "Newly above threshold"

    return "Above in baseline"


def _velocity_bin(
    value: float,
    maximum: float,
) -> int:
    if maximum <= 0:
        return 0

    return min(
        int(
            value
            / maximum
            * len(_VELOCITY_COLORS)
        ),
        len(_VELOCITY_COLORS) - 1,
    )


def _pipe_hover_text(
    pipe_id: str,
    pipe: dict[str, Any] | None,
) -> str:
    if pipe is None:
        return (
            f"<b>{pipe_id}</b><br>"
            "No flushing scenario data"
        )

    threshold_status = (
        "Above threshold"
        if pipe.get("above_threshold")
        else "Below threshold"
    )

    return (
        f"<b>{pipe_id}</b><br>"
        f"Flow: "
        f"{float(pipe['flow_m3s']) * 1000.0:.3f} L/s<br>"
        f"Signed velocity: "
        f"{float(pipe['velocity_mps']):.3f} m/s<br>"
        f"Absolute velocity: "
        f"{float(pipe['absolute_velocity_mps']):.3f} m/s<br>"
        f"Baseline velocity: "
        f"{float(pipe['baseline_velocity_mps']):.3f} m/s<br>"
        f"{threshold_status}"
    )


def make_flushing_scenario_figure(
    network_view_state: dict[str, Any] | None,
    scenario_state: dict[str, Any] | None,
    *,
    map_mode: MapMode = "coverage",
    candidate_hydrant_ids: Sequence[str] = (),
) -> go.Figure:
    if not network_view_state:
        return make_empty_network_figure(
            "Upload a model to inspect flushing scenarios."
        )

    if not scenario_state:
        return make_empty_network_figure(
            "Select a flushing scenario to view its "
            "network result."
        )

    if map_mode not in {"coverage", "velocity"}:
        return make_empty_network_figure(
            "Unknown flushing map mode."
        )

    nodes = network_view_state.get("nodes", {})
    links = network_view_state.get("links", {})
    positions = _node_positions(nodes)

    if not positions:
        return make_empty_network_figure(
            "The loaded model has no valid node coordinates."
        )

    pipe_results = {
        str(row.get("pipe_id", "")): row
        for row in scenario_state.get("pipes", [])
        if row.get("pipe_id")
    }

    maximum_velocity = max(
        (
            float(
                row.get(
                    "absolute_velocity_mps",
                    0.0,
                )
            )
            for row in pipe_results.values()
        ),
        default=0.0,
    )

    coverage_groups = {
        name: {
            "x": [],
            "y": [],
        }
        for name in _COVERAGE_STYLES
    }

    velocity_groups = [
        {
            "x": [],
            "y": [],
        }
        for _ in _VELOCITY_COLORS
    ]

    missing_velocity = {
        "x": [],
        "y": [],
    }

    hover_x: list[float] = []
    hover_y: list[float] = []
    hover_text: list[str] = []

    for pipe_id, start_node, end_node in zip(
        links.get("id", []),
        links.get("start_node", []),
        links.get("end_node", []),
    ):
        start = positions.get(str(start_node))
        end = positions.get(str(end_node))

        if start is None or end is None:
            continue

        pipe_id = str(pipe_id)
        pipe = pipe_results.get(pipe_id)

        if map_mode == "coverage":
            group_name = _coverage_group(pipe)

            _append_segment(
                coverage_groups[group_name],
                start,
                end,
            )

        elif pipe is None:
            _append_segment(
                missing_velocity,
                start,
                end,
            )

        else:
            bin_id = _velocity_bin(
                float(
                    pipe[
                        "absolute_velocity_mps"
                    ]
                ),
                maximum_velocity,
            )

            _append_segment(
                velocity_groups[bin_id],
                start,
                end,
            )

        hover_x.append(
            (start[0] + end[0]) / 2.0
        )
        hover_y.append(
            (start[1] + end[1]) / 2.0
        )
        hover_text.append(
            _pipe_hover_text(
                pipe_id,
                pipe,
            )
        )

    figure = go.Figure()

    if map_mode == "coverage":
        for name, coordinates in (
            coverage_groups.items()
        ):
            if not coordinates["x"]:
                continue

            style = _COVERAGE_STYLES[name]

            figure.add_trace(
                go.Scattergl(
                    x=coordinates["x"],
                    y=coordinates["y"],
                    mode="lines",
                    line=style,
                    hoverinfo="skip",
                    name=name,
                )
            )

    else:
        if missing_velocity["x"]:
            figure.add_trace(
                go.Scattergl(
                    x=missing_velocity["x"],
                    y=missing_velocity["y"],
                    mode="lines",
                    line={
                        "color": "#cbd5e1",
                        "width": 0.7,
                    },
                    hoverinfo="skip",
                    name="No scenario data",
                )
            )

        for bin_id, coordinates in enumerate(
            velocity_groups
        ):
            if not coordinates["x"]:
                continue

            figure.add_trace(
                go.Scattergl(
                    x=coordinates["x"],
                    y=coordinates["y"],
                    mode="lines",
                    line={
                        "color": (
                            _VELOCITY_COLORS[
                                bin_id
                            ]
                        ),
                        "width": 1.7,
                    },
                    hoverinfo="skip",
                    name=(
                        f"Velocity bin "
                        f"{bin_id + 1}"
                    ),
                    showlegend=False,
                )
            )

        figure.add_trace(
            go.Scatter(
                x=[None, None],
                y=[None, None],
                mode="markers",
                marker={
                    "color": [
                        0.0,
                        maximum_velocity,
                    ],
                    "cmin": 0.0,
                    "cmax": max(
                        maximum_velocity,
                        1e-9,
                    ),
                    "colorscale": "Turbo",
                    "showscale": True,
                    "colorbar": {
                        "title": "|v| [m/s]",
                        "thickness": 12,
                    },
                },
                hoverinfo="skip",
                name="Velocity scale",
                showlegend=False,
            )
        )

    # Transparent midpoint markers provide per-pipe hover
    # without creating thousands of separate line traces.
    figure.add_trace(
        go.Scattergl(
            x=hover_x,
            y=hover_y,
            mode="markers",
            marker={
                "size": 9,
                "color": "rgba(0, 0, 0, 0)",
            },
            text=hover_text,
            hoverinfo="text",
            name="Pipe details",
            showlegend=False,
        )
    )

    node_ids = [
        str(value)
        for value in nodes.get("id", [])
    ]
    node_types = [
        str(value)
        for value in nodes.get("type", [])
    ]
    node_type_by_id = dict(
        zip(node_ids, node_types)
    )

    plotted_node_ids = [
        node_id
        for node_id in node_ids
        if node_id in positions
    ]

    figure.add_trace(
        go.Scattergl(
            x=[
                positions[node_id][0]
                for node_id in plotted_node_ids
            ],
            y=[
                positions[node_id][1]
                for node_id in plotted_node_ids
            ],
            mode="markers",
            marker={
                "size": 4,
                "color": "#334155",
                "opacity": 0.65,
            },
            text=[
                (
                    f"<b>{node_id}</b><br>"
                    f"Type: "
                    f"{node_type_by_id.get(node_id, 'node')}"
                )
                for node_id in plotted_node_ids
            ],
            hoverinfo="text",
            name="Network nodes",
            showlegend=False,
        )
    )

    active_hydrants = (
        scenario_state.get("hydrants", [])
    )
    active_ids = {
        str(row.get("node_id", ""))
        for row in active_hydrants
    }

    candidate_ids = [
        node_id
        for node_id in dict.fromkeys(
            str(value)
            for value in candidate_hydrant_ids
        )
        if (
            node_id in positions
            and node_id not in active_ids
        )
    ]

    if candidate_ids:
        figure.add_trace(
            go.Scattergl(
                x=[
                    positions[node_id][0]
                    for node_id in candidate_ids
                ],
                y=[
                    positions[node_id][1]
                    for node_id in candidate_ids
                ],
                mode="markers",
                marker={
                    "size": 8,
                    "color": "#2563eb",
                    "line": {
                        "width": 1,
                        "color": "white",
                    },
                },
                text=[
                    f"Candidate hydrant: {node_id}"
                    for node_id in candidate_ids
                ],
                hoverinfo="text",
                name="Candidate hydrants",
            )
        )

    active_rows = [
        row
        for row in active_hydrants
        if str(
            row.get("node_id", "")
        ) in positions
    ]

    if active_rows:
        figure.add_trace(
            go.Scattergl(
                x=[
                    positions[
                        str(row["node_id"])
                    ][0]
                    for row in active_rows
                ],
                y=[
                    positions[
                        str(row["node_id"])
                    ][1]
                    for row in active_rows
                ],
                mode="markers",
                marker={
                    "size": 14,
                    "color": "#06b6d4",
                    "symbol": "circle-open-dot",
                    "line": {
                        "width": 2,
                        "color": "#083344",
                    },
                },
                text=[
                    (
                        f"<b>Open hydrant: "
                        f"{row['node_id']}</b><br>"
                        f"Flow: "
                        f"{float(row['flow_m3s']) * 1000.0:.2f} "
                        f"L/s<br>"
                        f"Pressure head: "
                        f"{float(row['pressure_head_m']):.2f} "
                        f"m<br>"
                        f"Status: "
                        f"{row.get('status', '')}"
                    )
                    for row in active_rows
                ],
                hoverinfo="text",
                name="Open hydrants",
            )
        )

    figure.update_layout(
        **FIG_LAYOUT,
        legend={
            "orientation": "h",
            "x": 0.0,
            "y": 1.02,
            "xanchor": "left",
            "yanchor": "bottom",
        },
        uirevision=(
            f"flushing-"
            f"{scenario_state.get('scenario_id', '')}-"
            f"{map_mode}"
        ),
    )

    return figure