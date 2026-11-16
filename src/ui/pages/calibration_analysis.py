# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dash_table, dcc, html
from dash.development.base_component import Component
from typing import Any

from src.ui import ids
from src.ui.pages.components import (
    create_page_header,
    create_run_section
)
from src.visualisation.calibration import (
    make_calibration_residual_figure,
    make_calibration_history_figure,
)


def _upload_box(
    component_id: str,
    title: str,
    subtitle: str,
    *,
    multiple: bool,
    disabled: bool = False,
):
    return dcc.Upload(
        id=component_id,
        className="model-upload calibration-upload",
        multiple=multiple,
        disabled=disabled,
        children=html.Div(
            children=[
                html.Div(
                    title,
                    className="model-upload-title",
                ),
                html.Div(
                    subtitle,
                    className="small-status",
                ),
            ]
        ),
    )


def _number_field(
    label: str,
    component_id: str,
    value: float | int | None,
    *,
    min_value: float | int | None = None,
    max_value: float | int | None = None,
    step: float | int | str = "any",
    disabled: bool = False,
):
    input_properties: dict[str, Any] = {
        "id": component_id,
        "type": "number",
        "value": value,
        "step": step,
        "disabled": disabled,
        "persistence": True,
        "persistence_type": "memory",
    }

    if min_value is not None:
        input_properties["min"] = min_value

    if max_value is not None:
        input_properties["max"] = max_value

    return html.Div(
        children=[
            dbc.Label(label),
            dbc.Input(**input_properties),
        ]
    )


def _create_optimizer_section():
    return html.Div(
        className="setup-section",
        children=[
            html.H3("Optimizer settings"),
            html.P(
                "Select the candidate pipes and configure the "
                "genetic optimizer. Larger populations and more "
                "generations improve the search but increase runtime."
            ),
            dbc.Label("Pipe selection"),
            dcc.Dropdown(
                id=ids.CAL_PIPE_SELECTION,
                options=[
                    {
                        "label": "Largest diameter pipes",
                        "value": "largest_diameter",
                    },
                    {
                        "label": "Most sensitive pipes",
                        "value": "most_sensitive",
                    },
                    {
                        "label": "Diameter cutoff",
                        "value": "Dmin",
                    },
                    {
                        "label": "Explicit pipe list",
                        "value": "list",
                    },
                    {
                        "label": "All pipes",
                        "value": "all",
                    },
                ],
                value="largest_diameter",
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            html.Div(
                className="calibration-options-grid",
                children=[
                    _number_field(
                        "Active pipe count",
                        ids.CAL_ACTIVE_PIPE_COUNT,
                        1,
                        min_value=1,
                        step=1,
                    ),
                    _number_field(
                        "Diameter cutoff [m]",
                        ids.CAL_DMIN,
                        None,
                        min_value=0,
                        disabled=True,
                    ),
                    _number_field(
                        "Minimum calibrated diameter [m]",
                        ids.CAL_MIN_DIAMETER,
                        None,
                        min_value=0,
                    ),
                    _number_field(
                        "Maximum calibrated diameter [m]",
                        ids.CAL_MAX_DIAMETER,
                        None,
                        min_value=0,
                    ),
                    _number_field(
                        "Pressure-error weight",
                        ids.CAL_PRESSURE_WEIGHT,
                        0.5,
                        min_value=0,
                        max_value=1,
                        step=0.05,
                    ),
                    _number_field(
                        "Period length [h]",
                        ids.CAL_PERIOD_HOURS,
                        0.01,
                        min_value=0.001,
                    ),
                    _number_field(
                        "Population size",
                        ids.CAL_POPSIZE,
                        20,
                        min_value=1,
                        step=1,
                    ),
                    _number_field(
                        "Generations",
                        ids.CAL_NGEN,
                        50,
                        min_value=1,
                        step=1,
                    ),
                    _number_field(
                        "Mutation probability",
                        ids.CAL_PMUT,
                        0.2,
                        min_value=0,
                        max_value=1,
                        step=0.05,
                    ),
                    _number_field(
                        "Crossover probability",
                        ids.CAL_PCROSS,
                        0.8,
                        min_value=0,
                        max_value=1,
                        step=0.05,
                    ),
                    _number_field(
                        "Random seed",
                        ids.CAL_SEED,
                        12345,
                        min_value=0,
                        step=1,
                    ),
                ],
            ),
            dbc.Label(
                "Explicit pipe IDs",
                className="mt-3",
            ),
            dbc.Textarea(
                id=ids.CAL_PIPE_IDS,
                placeholder="P1, P2, P3",
                rows=3,
                disabled=True,
                persistence=True,
                persistence_type="memory",
            ),
            html.Div(
                (
                    "Pressure-error weight: 1 uses only nodal "
                    "pressure errors; 0 uses only tank-level errors."
                ),
                className="small-status mt-2",
            ),
        ],
    )


def _empty_results():
    return html.Div(
        className="calibration-results-placeholder",
        children=[
            html.Div(
                "🎯",
                className="calibration-placeholder-icon",
            ),
            html.H3("No calibration result yet"),
            html.P(
                "Prepare the network snapshots and measurement "
                "dataset. Optimizer controls and execution will "
                "be added in the next step."
            ),
        ],
    )


def _metric(label: str, value: str):
    return html.Div(
        className="meta-item",
        children=[
            html.Div(label, className="meta-label"),
            html.Div(value, className="meta-value"),
        ],
    )


def _format_number(
    value: Any,
    *,
    digits: int,
) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def render_calibration_results(
    run_state: dict[str, Any] | None,
):
    if not run_state:
        return _empty_results()

    summary = run_state.get("summary", {})
    pipes = run_state.get("pipes", [])
    warnings = (
        run_state.get("staci", {})
        .get("warnings", [])
    )

    content: list[Component] = [
        html.Div(
            className="meta-grid calibration-meta-grid",
            children=[
                _metric(
                    "Status",
                    str(
                        run_state.get("status", "—")
                    ).title(),
                ),
                _metric(
                    "Snapshots",
                    str(
                        summary.get(
                            "snapshot_count",
                            "—",
                        )
                    ),
                ),
                _metric(
                    "Measurements",
                    str(
                        summary.get(
                            "measurement_count",
                            "—",
                        )
                    ),
                ),
                _metric(
                    "Calibrated pipes",
                    str(
                        summary.get(
                            "calibrated_pipe_count",
                            "—",
                        )
                    ),
                ),
            ],
        )
    ]

    if warnings:
        content.append(
            dbc.Alert(
                children=[
                    html.Div(
                        "Calibration completed with warnings.",
                        style={"fontWeight": 800},
                    ),
                    html.Ul(
                        [
                            html.Li(str(message))
                            for message in warnings
                        ],
                        className="mb-0 mt-2",
                    ),
                ],
                color="warning",
                className="mt-3",
            )   #
        )

    if pipes:
        rows = []

        for pipe in pipes:
            diameter = float(pipe["diameter_m"])
            ratio = float(pipe["diameter_ratio"])
            diameter = float(pipe["diameter_m"])
            ratio = float(pipe["diameter_ratio"])

            original_diameter = diameter / ratio
            calibrated_diameter = diameter

            rows.append(
                html.Tr(
                    [
                        html.Td(pipe["pipe_id"]),
                        html.Td(html.Td(_format_number(original_diameter, digits=4))),
                        html.Td(html.Td(_format_number(ratio, digits=4))),
                        html.Td(html.Td(_format_number(calibrated_diameter, digits=4))),
                    ]
                )
            )

        content.extend(
            [
                html.H3(
                    "Calibrated pipe diameters",
                    className="calibration-result-heading",
                ),
                html.Div(
                    className="calibration-pipe-table-wrap",
                    children=dbc.Table(
                        children=[
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th("Pipe ID"),
                                        html.Th(
                                            "Original diameter [m]"
                                        ),
                                        html.Th(
                                            "Diameter multiplier [-]"
                                        ),
                                        html.Th(
                                            "Calibrated diameter [m]"
                                        ),
                                    ]
                                )
                            ),
                            html.Tbody(rows),
                        ],
                        bordered=False,
                        hover=True,
                        striped=True,
                        className="calibration-pipe-table",
                    ),
                ),
            ]
        )
    else:
        content.append(
            dbc.Alert(
                "No calibrated pipe results were produced.",
                color="secondary",
                className="mt-3",
            )
        )

    content.extend(
        [
            html.Div(
                className="calibration-result-plots",
                children=[
                    html.Div(
                        children=[
                            html.H3(
                                "Optimizer convergence (sampled every 10 generations).",
                                className=(
                                    "calibration-result-heading"
                                ),
                            ),
                            dcc.Graph(
                                id=ids.CAL_HISTORY_GRAPH,
                                figure=(
                                    make_calibration_history_figure(
                                        run_state
                                    )
                                ),
                                config={
                                    "displaylogo": False,
                                },
                            ),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.H3(
                                "Calibration residuals",
                                className=(
                                    "calibration-result-heading"
                                ),
                            ),
                            dcc.Graph(
                                id=ids.CAL_RESIDUAL_GRAPH,
                                figure=(
                                    make_calibration_residual_figure(
                                        run_state
                                    )
                                ),
                                config={
                                    "displaylogo": False,
                                },
                            ),
                        ]
                    ),
                ],
            )
        ]
    )

    return content


def _create_input_card():
    return dbc.Card(
        className="app-card calibration-input-card",
        children=[
            dbc.CardHeader("Calibration Inputs"),
            dbc.CardBody(
                children=[
                    html.Div(
                        className="setup-section",
                        children=[
                            html.H3("Network snapshots"),
                            html.P(
                                "Upload one EPANET INP file for "
                                "each operating period. Upload "
                                "order defines period order."
                            ),
                            _upload_box(
                                ids.CAL_UPLOAD_SNAPSHOTS,
                                "Drop INP snapshots here",
                                "or click to select multiple files",
                                multiple=True,
                            ),
                            html.Div(
                                id=(
                                    ids.CAL_SNAPSHOT_UPLOAD_STATUS
                                ),
                                className=(
                                    "small-status upload-status"
                                ),
                            ),
                        ],
                    ),
                    html.Hr(),
                    html.Div(
                        className="setup-section",
                        children=[
                            html.H3("Included periods"),
                            html.P(
                                "Uncheck snapshots that should be "
                                "ignored. Included periods will be "
                                "reindexed before execution."
                            ),
                            dbc.Checklist(
                                id=ids.CAL_SNAPSHOT_SELECTION,
                                options=[],
                                value=[],
                                className=(
                                    "calibration-snapshot-list"
                                ),
                                persistence=True,
                                persistence_type="memory",
                            ),
                        ],
                    ),
                    html.Hr(),
                    html.Div(
                        className="setup-section",
                        children=[
                            html.H3("Measurements"),
                            html.P(
                                "Upload pressure-head and tank-level "
                                "measurements as JSON, or create and "
                                "edit rows in the table."
                            ),
                            _upload_box(
                                ids.CAL_UPLOAD_MEASUREMENTS,
                                "Drop measurements JSON here",
                                "Upload snapshots first",
                                multiple=False,
                                disabled=True,
                            ),
                            html.Div(
                                id=ids.CAL_MEASUREMENTS_STATUS,
                                className=(
                                    "small-status upload-status"
                                ),
                            ),
                        ],
                    ),
                    html.Hr(),
                    html.Div(
                        id=ids.CAL_INPUT_SUMMARY,
                        className="soft-panel",
                        children=(
                            "Upload network snapshots to begin."
                        ),
                    ),
                    html.Hr(),
                    _create_optimizer_section(),
                    html.Hr(),
                    create_run_section(
                        "Run Calibration",
                        ids.CAL_RUN_BUTTON,
                        ids.CAL_RUN_STATUS,
                        status_class_name="calibration-run-status"
                    ),
                ]
            ),
        ],
    )


def _create_workspace_card():
    return dbc.Card(
        className="app-card calibration-workspace-card",
        children=[
            dbc.CardHeader("Measurements & Results"),
            dbc.CardBody(
                children=[
                    html.Div(
                        className=(
                            "calibration-table-header"
                        ),
                        children=[
                            html.Div(
                                children=[
                                    html.H3(
                                        "Measurement editor"
                                    ),
                                    html.P(
                                        "Node values are pressure "
                                        "head in metres. Pool values "
                                        "are water depth above the "
                                        "tank bottom in metres."
                                    ),
                                ]
                            ),
                            dbc.Button(
                                "Add row",
                                id=ids.CAL_ADD_MEASUREMENT,
                                color="secondary",
                                outline=True,
                                size="sm",
                                n_clicks=0,
                            ),
                        ],
                    ),
                    dash_table.DataTable(
                        id=ids.CAL_MEASUREMENTS_TABLE,
                        columns=[
                            {
                                "name": "Element ID",
                                "id": "id",
                                "type": "text",
                            },
                            {
                                "name": "Type",
                                "id": "type",
                                "presentation": "dropdown",
                            },
                        ],
                        data=[],
                        editable=True,
                        row_deletable=True,
                        dropdown={
                            "type": {
                                "options": [
                                    {
                                        "label": "Node",
                                        "value": "node",
                                    },
                                    {
                                        "label": "Pool",
                                        "value": "pool",
                                    },
                                ]
                            }
                        },
                        persistence=True,
                        persistence_type="memory",
                        persisted_props=["data"],
                        fixed_rows={"headers": True},
                        style_table={
                            "height": "420px",
                            "maxHeight": "420px",
                            "overflowX": "auto",
                            "overflowY": "auto",
                        },
                        style_header={
                            "fontWeight": "700",
                            "backgroundColor": "#f0f9ff",
                        },
                        style_cell={
                            "minWidth": "120px",
                            "width": "120px",
                            "maxWidth": "180px",
                            "whiteSpace": "normal",
                            "textAlign": "left",
                        },
                    ),
                    html.Hr(),
                    html.Div(
                        id=ids.CAL_RESULTS,
                        children=_empty_results(),
                    ),
                ]
            ),
        ],
    )


def create_layout():
    return html.Div(
        className="page calibration-page",
        children=[
            create_page_header(
                "Pipe Diameter Calibration",
                (
                    "Estimate selected pipe diameters from "
                    "multiple steady-state network snapshots "
                    "and measured pressure or tank-level data."
                ),
                "STACI Calibrate",
            ),
            html.Div(
                className=(
                    "analysis-workspace "
                    "calibration-workspace"
                ),
                children=[
                    _create_input_card(),
                    _create_workspace_card(),
                ],
            ),
        ],
    )