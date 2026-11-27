import base64

import pytest

from src.ui.callbacks.helpers import (
    decode_upload_contents,
    finite_number,
    nonnegative_number,
    positive_number,
    resolve_color_range_outputs,
    round_color_range_value,
)


def test_decode_upload_contents_returns_bytes() -> None:
    payload = b"[TITLE]\nTest network\n"
    encoded = base64.b64encode(payload).decode("ascii")

    contents = f"data:application/octet-stream;base64,{encoded}"

    assert decode_upload_contents(contents) == payload


@pytest.mark.parametrize(
    "contents",
    [
        None,
        "",
        "missing-comma",
        "data:application/octet-stream;base64,invalid!",
    ],
)
def test_decode_upload_contents_rejects_invalid_data(
    contents: str | None,
) -> None:
    with pytest.raises(ValueError):
        decode_upload_contents(contents)


@pytest.mark.parametrize(
    "value",
    [
        None,
        "invalid",
        True,
        float("nan"),
        float("inf"),
    ],
)
def test_finite_number_rejects_invalid_values(
    value,
) -> None:
    with pytest.raises(ValueError):
        finite_number(
            value,
            "Test value",
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "invalid",
        0,
        -1,
        float("inf"),
    ],
)
def test_positive_number_rejects_invalid_values(
    value,
) -> None:
    with pytest.raises(ValueError):
        positive_number(
            value,
            "Test value",
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        "invalid",
        -1,
        float("nan"),
    ],
)
def test_nonnegative_number_rejects_invalid_values(
    value,
) -> None:
    with pytest.raises(ValueError):
        nonnegative_number(
            value,
            "Test value",
        )


def test_numeric_validators_accept_valid_values() -> None:
    assert positive_number(
        "0.002",
        "Area",
    ) == pytest.approx(0.002)

    assert nonnegative_number(
        0,
        "Threshold",
    ) == pytest.approx(0.0)


def test_color_range_values_use_attribute_precision() -> None:
    assert (
        round_color_range_value(
            "head",
            123.456789,
        )
        == 123.46
    )

    assert (
        round_color_range_value(
            "velocity",
            0.123456789,
        )
        == 0.1235
    )

    assert (
        round_color_range_value(
            "flowrate",
            0.00123456789,
        )
        == 0.001235
    )


def test_color_range_value_handles_missing_value() -> None:
    assert (
        round_color_range_value(
            "head",
            None,
        )
        is None
    )


def test_resolve_color_range_outputs() -> None:
    assert resolve_color_range_outputs(
        {
            "pressure": {
                "min": 12.3456,
                "max": 34.5678,
            }
        },
        "pressure",
    ) == (
        12.35,
        34.57,
        False,
        False,
    )


def test_missing_color_range_disables_controls() -> None:
    assert resolve_color_range_outputs(
        {},
        "pressure",
    ) == (
        None,
        None,
        True,
        True,
    )
