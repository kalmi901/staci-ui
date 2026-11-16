from __future__ import annotations

import base64
import logging
import math
import re
from typing import Any

import dash_bootstrap_components as dbc
from dash import (
    Input,
    Output,
    State,
    html
)
from dash.exceptions import PreventUpdate

from src.run_logging import logged_run
from src.services.calibration_runner import call_staci_calibrate_service
from src.services.calibration_storage import (
    resolve_calibration_snapshots,
    store_calibration_measurements,
    store_calibration_snapshots,
)
from src.ui import ids
from src.ui.pages.calibration_analysis import render_calibration_results


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


def _finite_number(
    value: Any,
    label: str,
) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a number.")

    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{label} must be a number."
        ) from exc

    if not math.isfinite(number):
        raise ValueError(
            f"{label} must be a finite number."
        )

    return number


def _positive_number(
    value: Any,
    label: str,
) -> float:
    number = _finite_number(value, label)

    if number <= 0:
        raise ValueError(
            f"{label} must be greater than zero."
        )

    return number


def _optional_positive_number(
    value: Any,
    label: str,
) -> float | None:
    if value in (None, ""):
        return None

    return _positive_number(value, label)


def _positive_integer(
    value: Any,
    label: str,
) -> int:
    number = _positive_number(value, label)

    if not number.is_integer():
        raise ValueError(
            f"{label} must be an integer."
        )

    return int(number)


def _nonnegative_integer(
    value: Any,
    label: str,
) -> int:
    number = _finite_number(value, label)

    if number < 0 or not number.is_integer():
        raise ValueError(
            f"{label} must be a non-negative integer."
        )

    return int(number)


def _probability(
    value: Any,
    label: str,
) -> float:
    number = _finite_number(value, label)

    if number < 0 or number > 1:
        raise ValueError(
            f"{label} must be between 0 and 1."
        )

    return number


def _parse_pipe_ids(
    value: str | None,
) -> list[str]:
    pipe_ids = [
        part.strip()
        for part in re.split(
            r"[,;\r\n]+",
            value or "",
        )
        if part.strip()
    ]

    if not pipe_ids:
        raise ValueError(
            "Enter at least one pipe ID."
        )

    if len(set(pipe_ids)) != len(pipe_ids):
        raise ValueError(
            "Pipe IDs must be unique."
        )

    return pipe_ids


def _prepare_calibration_inputs(
    snapshot_state: dict[str, Any] | None,
    selected_snapshots: list[str] | None,
    measurement_rows: list[dict[str, Any]] | None,
) -> tuple[list[str], dict[str, Any]]:
    if not snapshot_state:
        raise ValueError(
            "Upload calibration INP snapshots first."
        )

    snapshots = snapshot_state.get("snapshots", [])

    if not isinstance(snapshots, list) or not snapshots:
        raise ValueError(
            "No calibration snapshots are available."
        )

    selected = {
        str(filename)
        for filename in (selected_snapshots or [])
    }

    if not selected:
        raise ValueError(
            "Include at least one calibration snapshot."
        )

    available = {
        str(snapshot["stored_filename"])
        for snapshot in snapshots
    }

    unknown = selected - available

    if unknown:
        raise ValueError(
            "The snapshot selection contains unknown files."
        )

    included_snapshots = [
        snapshot
        for snapshot in snapshots
        if str(snapshot["stored_filename"]) in selected
    ]

    if not measurement_rows:
        raise ValueError(
            "Enter at least one calibration measurement."
        )

    measurements: list[dict[str, Any]] = []
    measurement_ids: set[str] = set()

    for row_index, row in enumerate(measurement_rows):
        measurement_id = str(
            row.get("id", "")
        ).strip()

        if not measurement_id:
            raise ValueError(
                "Measurement row "
                f"{row_index + 1} requires an element ID."
            )

        if measurement_id in measurement_ids:
            raise ValueError(
                "Measurement IDs must be unique: "
                f"{measurement_id!r}."
            )

        measurement_type = str(
            row.get("type", "")
        ).lower()

        if measurement_type not in {"node", "pool"}:
            raise ValueError(
                f"Measurement {measurement_id!r} must "
                "have type 'node' or 'pool'."
            )

        values: list[float] = []

        for snapshot in included_snapshots:
            period_index = int(
                snapshot["period_index"]
            )
            field = f"value_{period_index}"

            values.append(
                _finite_number(
                    row.get(field),
                    (
                        f"Measurement {measurement_id!r}, "
                        f"period {period_index}"
                    ),
                )
            )

        measurement_ids.add(measurement_id)
        measurements.append(
            {
                "id": measurement_id,
                "type": measurement_type,
                "values": values,
            }
        )

    stored_filenames = [
        str(snapshot["stored_filename"])
        for snapshot in included_snapshots
    ]

    return stored_filenames, {
        "measurements": measurements,
    }


def _build_optimizer_settings(
    *,
    pipe_selection: Any,
    active_pipe_count: Any,
    pipe_ids: str | None,
    dmin: Any,
    min_diameter: Any,
    max_diameter: Any,
    pressure_weight: Any,
    period_hours: Any,
    popsize: Any,
    ngen: Any,
    pmut: Any,
    pcross: Any,
) -> dict[str, Any]:
    supported_selections = {
        "largest_diameter",
        "most_sensitive",
        "Dmin",
        "list",
        "all",
    }

    if pipe_selection not in supported_selections:
        raise ValueError(
            "Select a valid pipe-selection method."
        )

    settings: dict[str, Any] = {
        "type_of_pipe_selection": pipe_selection,
        "weight_p_err": _probability(
            pressure_weight,
            "Pressure-error weight",
        ),
        "dt": _positive_number(
            period_hours,
            "Period length",
        ),
        "popsize": _positive_integer(
            popsize,
            "Population size",
        ),
        "ngen": _positive_integer(
            ngen,
            "Generation count",
        ),
        "pmut": _probability(
            pmut,
            "Mutation probability",
        ),
        "pcross": _probability(
            pcross,
            "Crossover probability",
        ),
    }

    if pipe_selection in {
        "largest_diameter",
        "most_sensitive",
    }:
        settings["num_of_active_pipes"] = (
            _positive_integer(
                active_pipe_count,
                "Active pipe count",
            )
        )

    elif pipe_selection == "Dmin":
        settings["Dmin"] = _positive_number(
            dmin,
            "Diameter cutoff",
        )

    elif pipe_selection == "list":
        settings["pipe_ids"] = _parse_pipe_ids(
            pipe_ids
        )

    minimum = _optional_positive_number(
        min_diameter,
        "Minimum calibrated diameter",
    )
    maximum = _optional_positive_number(
        max_diameter,
        "Maximum calibrated diameter",
    )

    if (
        minimum is not None
        and maximum is not None
        and minimum >= maximum
    ):
        raise ValueError(
            "Minimum calibrated diameter must be "
            "less than maximum calibrated diameter."
        )

    if minimum is not None:
        settings["min_diameter_m"] = minimum

    if maximum is not None:
        settings["max_diameter_m"] = maximum

    return settings


def register_calibration_callbacks(app):
    @app.callback(
        Output(ids.CAL_ACTIVE_PIPE_COUNT, "disabled"),
        Output(ids.CAL_PIPE_IDS, "disabled"),
        Output(ids.CAL_DMIN, "disabled"),
        Input(ids.CAL_PIPE_SELECTION, "value"),
    )
    def toggle_pipe_selection_controls(pipe_selection):
        return (
            pipe_selection not in {
                "largest_diameter",
                "most_sensitive",
            },
            pipe_selection != "list",
            pipe_selection != "Dmin",
        )


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
        Output(ids.CAL_RUN_BUTTON, "disabled"),
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
            return True, "Upload network snapshots to begin.", True

        total_count = len(snapshot_state.get("snapshots", []))
        included_count = len(selected_snapshots or [])
        measurement_count = len(measurement_rows or [])
        inputs_ready = bool(included_count and measurement_count)

        return (
            False,
            [
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
        ],
        not inputs_ready
        )


    @app.callback(
        Output(ids.CAL_RUN_STORE, "data"),
        Output(ids.CAL_RUN_STATUS, "children"),
        Input(ids.CAL_RUN_BUTTON, "n_clicks"),
        State(ids.CAL_SNAPSHOT_STORE, "data"),
        State(ids.CAL_SNAPSHOT_SELECTION, "value"),
        State(ids.CAL_MEASUREMENTS_TABLE, "data"),
        State(ids.CAL_PIPE_SELECTION, "value"),
        State(ids.CAL_ACTIVE_PIPE_COUNT, "value"),
        State(ids.CAL_PIPE_IDS, "value"),
        State(ids.CAL_DMIN, "value"),
        State(ids.CAL_MIN_DIAMETER, "value"),
        State(ids.CAL_MAX_DIAMETER, "value"),
        State(ids.CAL_PRESSURE_WEIGHT, "value"),
        State(ids.CAL_PERIOD_HOURS, "value"),
        State(ids.CAL_POPSIZE, "value"),
        State(ids.CAL_NGEN, "value"),
        State(ids.CAL_PMUT, "value"),
        State(ids.CAL_PCROSS, "value"),
        State(ids.CAL_SEED, "value"),
        background=True,
        running=[
            (
                Output(ids.CAL_RUN_BUTTON, "disabled"),
                True,
                False,
            ),
        ],
        prevent_initial_call=True,
    )
    @logged_run("calibration")
    def run_calibration(
        n_clicks,
        snapshot_state,
        selected_snapshots,
        measurement_rows,
        pipe_selection,
        active_pipe_count,
        pipe_ids,
        dmin,
        min_diameter,
        max_diameter,
        pressure_weight,
        period_hours,
        popsize,
        ngen,
        pmut,
        pcross,
        seed,
    ):
        if not n_clicks:
            raise PreventUpdate

        try:
            (
                stored_filenames,
                measurements,
            ) = _prepare_calibration_inputs(
                snapshot_state,
                selected_snapshots,
                measurement_rows,
            )

            optimizer_settings = (
                _build_optimizer_settings(
                    pipe_selection=pipe_selection,
                    active_pipe_count=active_pipe_count,
                    pipe_ids=pipe_ids,
                    dmin=dmin,
                    min_diameter=min_diameter,
                    max_diameter=max_diameter,
                    pressure_weight=pressure_weight,
                    period_hours=period_hours,
                    popsize=popsize,
                    ngen=ngen,
                    pmut=pmut,
                    pcross=pcross,
                )
            )

            seed_value = _nonnegative_integer(
                seed,
                "Random seed",
            )

            snapshot_paths = (
                resolve_calibration_snapshots(
                    snapshot_state["upload_id"],
                    stored_filenames,
                )
            )

            logger.info(
                "Calibration started: "
                "upload_id=%s snapshots=%d "
                "measurements=%d selection=%s",
                snapshot_state.get("upload_id", ""),
                len(snapshot_paths),
                len(measurements["measurements"]),
                pipe_selection,
            )

            run_state = call_staci_calibrate_service(
                snapshot_paths,
                measurements=measurements,
                optimizer_settings=optimizer_settings,
                seed=seed_value,
            )

            logger.info(
                "Calibration finished: "
                "run_id=%s snapshots=%s "
                "measurements=%s pipes=%s",
                run_state.get("run_id", ""),
                run_state.get(
                    "summary", {}
                ).get("snapshot_count", ""),
                run_state.get(
                    "summary", {}
                ).get("measurement_count", ""),
                run_state.get(
                    "summary", {}
                ).get("calibrated_pipe_count", ""),
            )

        except Exception as exc:
            logger.exception(
                "Calibration failed: upload_id=%s",
                (
                    snapshot_state.get("upload_id", "")
                    if snapshot_state
                    else ""
                ),
            )

            return None, dbc.Alert(
                f"Calibration failed: {exc}",
                color="danger",
                className="upload-alert",
            )

        warnings = (
            run_state.get("staci", {})
            .get("warnings", [])
        )
        summary = run_state.get("summary", {})

        return run_state, dbc.Alert(
            children=[
                html.Div(
                    (
                        "Calibration completed with warnings."
                        if warnings
                        else "Calibration completed successfully."
                    ),
                    style={"fontWeight": 800},
                ),
                html.Div(
                    f"Run ID: {run_state['run_id']} · "
                    f"Snapshots: "
                    f"{summary.get('snapshot_count', 0)} · "
                    f"Measurements: "
                    f"{summary.get('measurement_count', 0)} · "
                    f"Calibrated pipes: "
                    f"{summary.get('calibrated_pipe_count', 0)}"
                ),
            ],
            color=(
                "warning"
                if warnings
                else "success"
            ),
            className="upload-alert",
        )


    @app.callback(
        Output(ids.CAL_RESULTS, "children"),
        Input(ids.CAL_RUN_STORE, "data"),
    )
    def render_results(run_state):
        return render_calibration_results(run_state)