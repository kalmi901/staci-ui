from __future__ import annotations

from typing import Any
import plotly.graph_objects as go
from collections.abc import Sequence


NETWORK_FIGURE_LAYOUT = {
    "template": "plotly_white",
    "height": 470,
    "margin": {
        "l": 10,
        "r": 10,
        "t": 10,
        "b": 10,
    },
    "xaxis": {
        "visible": False,
        "showgrid": False,
        "zeroline": False,
        "scaleanchor": "y",
        "scaleratio": 1,
    },
    "yaxis": {
        "visible": False,
        "showgrid": False,
        "zeroline": False,
    },
}


def make_discrete_colorscale(
    colors: Sequence[str]
) -> list[list[float | str]]:
    if not colors:
        raise ValueError(
            "At least one color is required."
        )

    colorscale: list[list[float | str]] = []
    color_count = len(colors)

    for index, color in enumerate(colors):
        lower = index / color_count
        upper = (index + 1) / color_count

        colorscale.extend(
            [
                [lower, color],
                [upper, color],
            ]
        )

    return colorscale


def node_positions(
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


def append_line_segment(
    coordinates: dict[str, list[float | None]],
    start: tuple[float, float],
    end: tuple[float, float],
) -> None:
    coordinates["x"].extend(
        [start[0], end[0], None]
    )
    coordinates["y"].extend(
        [start[1], end[1], None]
    )


def model_ids_are_compatible(
    first_state: dict[str, Any],
    second_state: dict[str, Any],
) -> bool:
    first_model_id = first_state.get("model_id")
    second_model_id = second_state.get("model_id")

    return not (
        first_model_id
        and second_model_id
        and first_model_id != second_model_id
    )


def apply_network_layout(
    figure: go.Figure,
    *,
    uirevision: str | None = None,
    title: dict[str, Any] | str | None = None,
    legend: dict[str, Any] | None = None,
) -> go.Figure:
    overrides: dict[str, Any] = {}

    if uirevision is not None:
        overrides["uirevision"] = uirevision

    if title is not None:
        overrides["title"] = title

    if legend is not None:
        overrides["legend"] = legend

    figure.update_layout(
        **NETWORK_FIGURE_LAYOUT,
        **overrides,
    )

    return figure


def make_empty_network_figure(
    message: str = (
        "Upload a model to view the network preview."
    ),
) -> go.Figure:
    figure = go.Figure()

    figure.update_layout(
        **NETWORK_FIGURE_LAYOUT,
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {
                    "size": 15,
                    "color": "#6b7280",
                },
            }
        ],
    )

    return figure