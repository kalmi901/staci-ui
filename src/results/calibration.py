from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CalibratedPipe:
    pipe_id: str
    diameter_m: float
    diameter_ratio: float


@dataclass(frozen=True)
class CalibrationComparison:
    period_index: int
    measurement_id: str
    measured_value: float
    computed_value: float


@dataclass(frozen=True)
class CalibrationBestResult:
    pipes: tuple[CalibratedPipe, ...]
    comparisons: tuple[CalibrationComparison, ...]


@dataclass(frozen=True)
class CalibrationHistoryEntry:
    generation: int
    function_evaluations: int
    best_objective: float
    improvement: float


def _read_lines(path: Path, description: str) -> list[str]:
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            f"{description} file not found: {path}"
        )

    lines = [
        line.strip()
        for line in path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
        if line.strip()
    ]

    if not lines:
        raise ValueError(f"{description} file is empty: {path}")

    return lines


def _fields(line: str) -> list[str]:
    return [
        field.strip()
        for field in line.split(";")
        if field.strip()
    ]


def _finite_float(
    value: str,
    *,
    field: str,
) -> float:
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid numeric value for {field}: {value!r}"
        ) from exc

    if not math.isfinite(result):
        raise ValueError(
            f"Non-finite numeric value for {field}: {value!r}"
        )

    return result


def parse_calibration_best(
    path: Path,
) -> CalibrationBestResult:
    lines = _read_lines(path, "STACI calibration best result")

    if len(lines) < 5:
        raise ValueError(
            "STACI calibration best result has too few rows."
        )

    pipe_ids = _fields(lines[0])
    diameters = _fields(lines[1])
    ratios = _fields(lines[2])

    if not pipe_ids:
        raise ValueError(
            "STACI calibration result contains no calibrated pipes."
        )

    if not (
        len(pipe_ids) == len(diameters) == len(ratios)
    ):
        raise ValueError(
            "STACI calibration pipe result column counts differ."
        )

    pipes = tuple(
        CalibratedPipe(
            pipe_id=pipe_id,
            diameter_m=_finite_float(
                diameter,
                field=f"diameter of pipe {pipe_id}",
            ),
            diameter_ratio=_finite_float(
                ratio,
                field=f"diameter ratio of pipe {pipe_id}",
            ),
        )
        for pipe_id, diameter, ratio in zip(
            pipe_ids,
            diameters,
            ratios,
        )
    )

    headers = _fields(lines[3])

    if not headers or len(headers) % 2 != 0:
        raise ValueError(
            "STACI calibration comparison header must contain "
            "measured/computed column pairs."
        )

    measurement_ids: list[str] = []

    for index in range(0, len(headers), 2):
        measured_header = headers[index]
        computed_header = headers[index + 1]

        if not measured_header.startswith("Sollwert "):
            raise ValueError(
                "Invalid measured-value header in STACI "
                f"calibration result: {measured_header!r}"
            )

        measurement_id = measured_header.removeprefix(
            "Sollwert "
        ).strip()

        if (
            not measurement_id
            or computed_header != measurement_id
        ):
            raise ValueError(
                "STACI calibration measured/computed "
                "headers do not match."
            )

        measurement_ids.append(measurement_id)

    comparisons: list[CalibrationComparison] = []

    for period_index, line in enumerate(lines[4:]):
        values = _fields(line)

        if len(values) != len(headers):
            raise ValueError(
                "STACI calibration comparison row "
                f"{period_index} has {len(values)} values; "
                f"expected {len(headers)}."
            )

        for measurement_index, measurement_id in enumerate(
            measurement_ids
        ):
            offset = 2 * measurement_index

            comparisons.append(
                CalibrationComparison(
                    period_index=period_index,
                    measurement_id=measurement_id,
                    measured_value=_finite_float(
                        values[offset],
                        field=(
                            f"measured value for "
                            f"{measurement_id}"
                        ),
                    ),
                    computed_value=_finite_float(
                        values[offset + 1],
                        field=(
                            f"computed value for "
                            f"{measurement_id}"
                        ),
                    ),
                )
            )

    return CalibrationBestResult(
        pipes=pipes,
        comparisons=tuple(comparisons),
    )


def parse_calibration_history(
    path: Path,
) -> tuple[CalibrationHistoryEntry, ...]:
    lines = _read_lines(path, "STACI calibration history")
    entries: list[CalibrationHistoryEntry] = []

    for row_index, line in enumerate(lines, start=1):
        values = _fields(line)

        if len(values) != 4:
            raise ValueError(
                "STACI calibration history row "
                f"{row_index} must contain four values."
            )

        try:
            generation = int(values[0])
            function_evaluations = int(values[1])
        except ValueError as exc:
            raise ValueError(
                "Invalid generation or function-evaluation "
                f"count in history row {row_index}."
            ) from exc

        if generation < 0 or function_evaluations < 0:
            raise ValueError(
                "Calibration history counters cannot be negative."
            )

        entries.append(
            CalibrationHistoryEntry(
                generation=generation,
                function_evaluations=function_evaluations,
                best_objective=_finite_float(
                    values[2],
                    field=f"best objective in row {row_index}",
                ),
                improvement=_finite_float(
                    values[3],
                    field=f"improvement in row {row_index}",
                ),
            )
        )

    return tuple(entries)