from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import plotly.graph_objects as go

DEFAULT_FIGURE_LAYOUT = {
    "template": "plotly_white",
    "height": 360,
    "margin": {
        "l": 55,
        "r": 25,
        "t": 25,
        "b": 55,
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


NETWORK_FIGURE_LAYOUT = {
    **DEFAULT_FIGURE_LAYOUT,
    "height": 470,
    "margin": {
        "l": 10,
        "r": 10,
        "t": 10,
        "b": 10,
    },
}


EMPTY_FIGURE_TONES = {
    "neutral": {
        "background": "rgba(240, 249, 255, 0.56)",
        "icon": "#137fc4",
        "title": "#14324a",
        "message": "#668295",
    },
    "warning": {
        "background": "rgba(255, 247, 237, 0.82)",
        "icon": "#d97706",
        "title": "#9a3412",
        "message": "#9a3412",
    },
    "danger": {
        "background": "rgba(254, 242, 242, 0.82)",
        "icon": "#dc2626",
        "title": "#991b1b",
        "message": "#7f1d1d",
    },
}


def normalize_display_value(
    value: Any,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    if not math.isfinite(number):
        return default

    return max(
        minimum,
        min(number, maximum),
    )


def make_discrete_colorscale(colors: Sequence[str]) -> list[list[float | str]]:
    if not colors:
        raise ValueError("At least one color is required.")

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
    coordinates["x"].extend([start[0], end[0], None])
    coordinates["y"].extend([start[1], end[1], None])


def model_ids_are_compatible(
    first_state: dict[str, Any],
    second_state: dict[str, Any],
) -> bool:
    first_model_id = first_state.get("model_id")
    second_model_id = second_state.get("model_id")

    return not (
        first_model_id and second_model_id and first_model_id != second_model_id
    )


def apply_figure_layout(
    figure: go.Figure,
    *,
    uirevision: str | None = None,
    layout: Mapping[str, Any] | None = None,
) -> go.Figure:
    resolved_layout = {
        **DEFAULT_FIGURE_LAYOUT,
        **dict(layout or {}),
    }

    if uirevision is not None:
        resolved_layout["uirevision"] = uirevision

    figure.update_layout(**resolved_layout)

    return figure


def apply_network_layout(
    figure: go.Figure,
    *,
    uirevision: str | None = None,
    title: dict[str, Any] | str | None = None,
    legend: dict[str, Any] | None = None,
) -> go.Figure:
    layout: dict[str, Any] = {
        **NETWORK_FIGURE_LAYOUT,
    }

    if title is not None:
        layout["title"] = title

    if legend is not None:
        layout["legend"] = legend

    return apply_figure_layout(
        figure,
        uirevision=uirevision,
        layout=layout,
    )


def make_empty_figure(
    message: str,
    *,
    icon: str | None = None,
    title: str | None = None,
    tone: str = "neutral",
    layout: Mapping[str, Any] | None = None,
) -> go.Figure:
    if tone not in EMPTY_FIGURE_TONES:
        raise ValueError(f"Unsupported empty-figure tone: {tone!r}")

    tone_style = EMPTY_FIGURE_TONES[tone]

    if tone == "warning":
        icon = icon or "!"
        title = title or "Check the selected data"

    if tone == "danger":
        icon = icon or "✕"
        title = title or "Unable to display results"

    decorated = bool(icon or title)

    annotations: list[dict[str, Any]] = [
        {
            "text": message,
            "xref": "paper",
            "yref": "paper",
            "x": 0.5,
            "y": 0.38 if decorated else 0.5,
            "showarrow": False,
            "align": "center",
            "font": {
                "size": 15,
                "color": tone_style["message"],
            },
        }
    ]

    if title:
        annotations.append(
            {
                "text": f"<b>{title}</b>",
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "align": "center",
                "font": {
                    "size": 20,
                    "color": tone_style["title"],
                },
            }
        )

    if icon:
        annotations.append(
            {
                "text": icon,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.64,
                "showarrow": False,
                "font": {
                    "size": 42,
                    "color": tone_style["icon"],
                },
            }
        )

    figure_layout = {
        **dict(layout or {}),
        "annotations": annotations,
    }

    if decorated:
        figure_layout.update(
            {
                "paper_bgcolor": tone_style["background"],
                "plot_bgcolor": tone_style["background"],
            }
        )

    return apply_figure_layout(
        go.Figure(),
        layout=figure_layout,
    )


def make_empty_network_figure(
    message: str = ("Upload a model to view the network preview."),
    *,
    icon: str | None = None,
    title: str | None = None,
    tone: str = "neutral",
) -> go.Figure:
    return make_empty_figure(
        message,
        icon=icon,
        title=title,
        tone=tone,
        layout=NETWORK_FIGURE_LAYOUT,
    )
