from __future__ import annotations

import base64
import math
from collections.abc import Mapping
from typing import Any


_COLOR_RANGE_DIGITS = {
    "elevation": 2,
    "length": 2,
    "roughness": 2,
    "head": 2,
    "pressure": 2,
    "diameter": 4,
    "velocity": 4,
    "headloss": 4,
    "demand": 6,
    "flowrate": 6,
}


def decode_upload_contents(
    contents: str | None,
) -> bytes:
    if not contents:
        raise ValueError("Missing upload contents.")

    try:
        _header, encoded = contents.split(",", 1)

        return base64.b64decode(
            encoded,
            validate=True,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Invalid uploaded file encoding."
        ) from exc


def finite_number(
    value: Any,
    label: str,
) -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"{label} must be a number."
        )

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


def positive_number(
    value: Any,
    label: str,
) -> float:
    number = finite_number(value, label)

    if number <= 0:
        raise ValueError(
            f"{label} must be greater than zero."
        )

    return number


def nonnegative_number(
    value: Any,
    label: str,
) -> float:
    number = finite_number(value, label)

    if number < 0:
        raise ValueError(
            f"{label} must be zero or greater."
        )

    return number


def round_color_range_value(
    attribute: str | None,
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    digits = _COLOR_RANGE_DIGITS.get(
        str(attribute),
        4,
    )

    return round(number, digits)


def resolve_color_range_outputs(
    ranges: Mapping[str, Any],
    attribute: str | None,
) -> tuple[
    float | None,
    float | None,
    bool,
    bool,
]:
    info = ranges.get(attribute or "", {})

    if not isinstance(info, Mapping):
        info = {}

    minimum = round_color_range_value(
        attribute,
        info.get("min"),
    )
    maximum = round_color_range_value(
        attribute,
        info.get("max"),
    )

    disabled = (
        minimum is None
        or maximum is None
    )

    return (
        minimum,
        maximum,
        disabled,
        disabled,
    )