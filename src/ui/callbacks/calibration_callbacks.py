from __future__ import annotations

import base64
import logging
from typing import Any

import dash_bootstrap_components as dbc
from dash import (
    Input,
    Output,
    State,
    ctx,
    no_update,
)
from dash.exceptions import PreventUpdate

from src.services.calibration_storage import (
    store_calibration_measurements,
    store_calibration_snapshots,
)
from src.ui import ids


logger = logging.getLogger(__name__)


def _decode_upload(contents: str) -> bytes:
    if not contents:
        raise ValueError("Missing upload contents.")

    try:
        _header, encoded = contents.split(",", 1)
        return base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "Invalid uploaded file encoding."
        ) from exc


def _measurement_columns(
    snapshot_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = [
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
    ]

    if not snapshot_state:
        return columns

    for snapshot in snapshot_state.get("snapshots", []):
        period_index = int(snapshot["period_index"])
        filename = snapshot.get("filename", "snapshot.inp")

        columns.append(
            {
                "name": (
                    f"Period {period_index} · {filename}"
                ),
                "id": f"value_{period_index}",
                "type": "numeric",
            }
        )

    return columns


def _measurement_rows(
    snapshot_state: dict[str, Any] | None,
    measurement_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not snapshot_state or not measurement_state:
        return []

    if (
        measurement_state.get("upload_id")
        != snapshot_state.get("upload_id")
    ):
        return []

    result: list[dict[str, Any]] = []
    measurements = (
        measurement_state.get("data", {})
        .get("measurements", [])
    )

    for measurement in measurements:
        values = measurement.get("values", [])
        row: dict[str, Any] = {
            "id": measurement.get("id", ""),
            "type": measurement.get("type", "node"),
        }

        for period_index, _snapshot in enumerate(
            snapshot_state.get("snapshots", [])
        ):
            row[f"value_{period_index}"] = (
                values[period_index]
                if period_index < len(values)
                else None
            )

        result.append(row)

    return result


def register_calibration_callbacks(app):
    @app.callback(
        Output(ids.CAL_SNAPSHOT_STORE, "data"),
        Output(
            ids.CAL_SNAPSHOT_UPLOAD_STATUS,
            "children",
        ),
        Output(ids.CAL_SNAPSHOT_SELECTION, "options"),
        Output(ids.CAL_SNAPSHOT_SELECTION, "value"),
        Output(
            ids.CAL_MEASUREMENT_STORE,
            "data",
            allow_duplicate=True,
        ),
        Input(ids.CAL_UPLOAD_SNAPSHOTS, "contents"),
        State(ids.CAL_UPLOAD_SNAPSHOTS, "filename"),
        prevent_initial_call=True,
    )
    def upload_snapshots(contents, filenames):
        if not contents:
            raise PreventUpdate

        if not isinstance(contents, list):
            contents = [contents]

        if not isinstance(filenames, list):
            filenames = [filenames]

        if len(contents) != len(filenames):
            return (
                None,
                dbc.Alert(
                    "Snapshot upload metadata is incomplete.",
                    color="danger",
                    className="upload-alert",
                ),
                [],
                [],
                None,
            )

        try:
            files = [
                (
                    filename,
                    _decode_upload(file_contents),
                )
                for filename, file_contents in zip(
                    filenames,
                    contents,
                    strict=True,
                )
            ]
            snapshot_state = (
                store_calibration_snapshots(files)
            )
        except Exception as exc:
            logger.exception(
                "Calibration snapshot upload failed."
            )
            return (
                None,
                dbc.Alert(
                    f"Snapshot upload failed: {exc}",
                    color="danger",
                    className="upload-alert",
                ),
                [],
                [],
                None,
            )

        options = [
            {
                "label": (
                    f"Period {snapshot['period_index']} · "
                    f"{snapshot['filename']} · "
                    f"{snapshot['size_bytes'] / 1024:.1f} KiB"
                ),
                "value": snapshot["stored_filename"],
            }
            for snapshot in snapshot_state["snapshots"]
        ]

        selected = [
            option["value"]
            for option in options
        ]

        logger.info(
            "Calibration snapshots uploaded: "
            "upload_id=%s snapshots=%d",
            snapshot_state["upload_id"],
            len(options),
        )

        return (
            snapshot_state,
            dbc.Alert(
                f"Uploaded {len(options)} INP snapshot(s).",
                color="success",
                className="upload-alert",
            ),
            options,
            selected,
            None,
        )

    @app.callback(
        Output(ids.CAL_MEASUREMENT_STORE, "data"),
        Output(ids.CAL_MEASUREMENTS_STATUS, "children"),
        Input(ids.CAL_UPLOAD_MEASUREMENTS, "contents"),
        State(ids.CAL_UPLOAD_MEASUREMENTS, "filename"),
        State(ids.CAL_SNAPSHOT_STORE, "data"),
        prevent_initial_call=True,
    )
    def upload_measurements(
        contents,
        filename,
        snapshot_state,
    ):
        if not contents:
            raise PreventUpdate

        if not snapshot_state:
            return None, dbc.Alert(
                "Upload INP snapshots first.",
                color="warning",
                className="upload-alert",
            )

        try:
            measurement_state = (
                store_calibration_measurements(
                    snapshot_state["upload_id"],
                    filename or "measurements.json",
                    _decode_upload(contents),
                )
            )
        except Exception as exc:
            logger.exception(
                "Calibration measurement upload failed."
            )
            return None, dbc.Alert(
                f"Measurement upload failed: {exc}",
                color="danger",
                className="upload-alert",
            )

        logger.info(
            "Calibration measurements uploaded: "
            "upload_id=%s filename=%s",
            snapshot_state["upload_id"],
            measurement_state["filename"],
        )

        return measurement_state, dbc.Alert(
            (
                f"Loaded "
                f"{len(measurement_state['data']['measurements'])} "
                "measurement row(s)."
            ),
            color="success",
            className="upload-alert",
        )

    @app.callback(
        Output(ids.CAL_MEASUREMENTS_TABLE, "columns"),
        Output(ids.CAL_MEASUREMENTS_TABLE, "data"),
        Input(ids.CAL_SNAPSHOT_STORE, "data"),
        Input(ids.CAL_MEASUREMENT_STORE, "data"),
    )
    def render_measurement_table(
        snapshot_state,
        measurement_state,
    ):
        return (
            _measurement_columns(snapshot_state),
            _measurement_rows(
                snapshot_state,
                measurement_state,
            ),
        )

    @app.callback(
        Output(
            ids.CAL_MEASUREMENTS_TABLE,
            "data",
            allow_duplicate=True,
        ),
        Input(ids.CAL_ADD_MEASUREMENT, "n_clicks"),
        State(ids.CAL_MEASUREMENTS_TABLE, "data"),
        State(ids.CAL_MEASUREMENTS_TABLE, "columns"),
        prevent_initial_call=True,
    )
    def add_measurement_row(
        n_clicks,
        current_rows,
        columns,
    ):
        if not n_clicks:
            raise PreventUpdate

        row: dict[str, Any] = {
            column["id"]: None
            for column in (columns or [])
        }
        row["id"] = ""
        row["type"] = "node"

        return [*(current_rows or []), row]

    @app.callback(
        Output(ids.CAL_UPLOAD_MEASUREMENTS, "disabled"),
        Output(ids.CAL_INPUT_SUMMARY, "children"),
        Input(ids.CAL_SNAPSHOT_STORE, "data"),
        Input(ids.CAL_SNAPSHOT_SELECTION, "value"),
        Input(ids.CAL_MEASUREMENTS_TABLE, "data"),
    )
    def update_input_summary(
        snapshot_state,
        selected_snapshots,
        measurement_rows,
    ):
        if not snapshot_state:
            return True, "Upload network snapshots to begin."

        total_count = len(snapshot_state.get("snapshots", []))
        included_count = len(selected_snapshots or [])
        measurement_count = len(measurement_rows or [])

        return False, [
            dbc.Badge(
                (
                    "Inputs ready"
                    if included_count and measurement_count
                    else "Inputs incomplete"
                ),
                color=(
                    "success"
                    if included_count and measurement_count
                    else "warning"
                ),
                className="mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        f"Snapshots: {included_count}/{total_count}"
                    ),
                    dbc.Col(
                        f"Measurements: {measurement_count}"
                    ),
                ],
                className="small-status",
            ),
        ]