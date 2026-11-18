from __future__ import annotations

from collections import defaultdict
from typing import Any

import plotly.graph_objects as go

from src.visualisation.common import (
    apply_figure_layout,
    make_empty_figure,
)


def make_calibration_history_figure(
    run_state: dict[str, Any] | None,
) -> go.Figure:
    history = (
        run_state.get("history", [])
        if run_state
        else []
    )

    if not history:
        return make_empty_figure(
            "No optimizer history is available."
        )

    generations = [
        row["generation"]
        for row in history
    ]
    objectives = [
        row["best_objective"]
        for row in history
    ]
    customdata = [
        [
            row["function_evaluations"],
            row["improvement"],
        ]
        for row in history
    ]

    figure = go.Figure(
        data=[
            go.Scatter(
                x=generations,
                y=objectives,
                mode="lines+markers",
                name="Best objective",
                customdata=customdata,
                line={
                    "color": "#2563eb",
                    "width": 2.5,
                },
                marker={
                    "size": 6,
                    "color": "#2563eb",
                },
                hovertemplate=(
                    "Generation: %{x}"
                    "<br>Best objective: %{y:.6g}"
                    "<br>Function evaluations: "
                    "%{customdata[0]}"
                    "<br>Improvement: "
                    "%{customdata[1]:.6g}"
                    "<extra></extra>"
                ),
            )
        ]
    )

    return apply_figure_layout(
        figure,
        uirevision=str(
            run_state.get(  # type: ignore
                "run_id",
                "calibration-run",
            )
        ),
        layout={
            "margin": {
                "l": 65,
                "r": 25,
                "t": 25,
                "b": 60,
            },
            "showlegend": False,
            "xaxis": {
                "title": "Generation",
                "rangemode": "tozero",
            },
            "yaxis": {
                "title": "Best objective",
            },
        },
    )


def make_calibration_residual_figure(
    run_state: dict[str, Any] | None,
) -> go.Figure:
    comparisons = (
        run_state.get("comparisons", [])
        if run_state
        else []
    )

    if not comparisons:
        return make_empty_figure(
            "No calibration residuals are available."
        )

    grouped: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for row in comparisons:
        grouped[
            str(row["measurement_id"])
        ].append(row)

    figure = go.Figure()

    for measurement_id, rows in grouped.items():
        ordered_rows = sorted(
            rows,
            key=lambda row: int(
                row["period_index"]
            ),
        )

        periods = [
            int(row["period_index"])
            for row in ordered_rows
        ]
        measured = [
            float(row["measured_value"])
            for row in ordered_rows
        ]
        computed = [
            float(row["computed_value"])
            for row in ordered_rows
        ]
        residuals = [
            computed_value - measured_value
            for measured_value, computed_value
            in zip(
                measured,
                computed,
                strict=True,
            )
        ]

        customdata = [
            [
                measured_value,
                computed_value,
            ]
            for measured_value, computed_value
            in zip(
                measured,
                computed,
                strict=True,
            )
        ]

        figure.add_trace(
            go.Scatter(
                x=periods,
                y=residuals,
                mode=(
                    "lines+markers"
                    if len(periods) > 1
                    else "markers"
                ),
                name=measurement_id,
                customdata=customdata,
                marker={"size": 9},
                line={"width": 2},
                hovertemplate=(
                    f"<b>{measurement_id}</b>"
                    "<br>Period: %{x}"
                    "<br>Measured: "
                    "%{customdata[0]:.4g} m"
                    "<br>Computed: "
                    "%{customdata[1]:.4g} m"
                    "<br>Residual: %{y:.4g} m"
                    "<extra></extra>"
                ),
            )
        )

    figure.add_hline(
        y=0,
        line={
            "color": "#64748b",
            "width": 2,
            "dash": "dash",
        },
    )

    return apply_figure_layout(
        figure,
        uirevision=str(
            run_state.get( # type: ignore
                "run_id",
                "calibration-run",
            )
        ),
        layout={
            "margin": {
                "l": 65,
                "r": 25,
                "t": 25,
                "b": 90,
            },
            "legend": {
                "orientation": "h",
                "x": 0,
                "y": -0.22,
                "xanchor": "left",
                "yanchor": "top",
            },
            "xaxis": {
                "title": "Period",
                "dtick": 1,
            },
            "yaxis": {
                "title": "Computed − measured [m]",
                "zeroline": False,
            },
        },
    )
