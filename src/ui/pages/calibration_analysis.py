# pylint: disable=not-callable
# pyright: reportCallIssue=false
from __future__ import annotations

from dash import dash_table, dcc, html
import dash_bootstrap_components as dbc

from src.ui import ids
from src.ui.pages.components import create_page_header


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