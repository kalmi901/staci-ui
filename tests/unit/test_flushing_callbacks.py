import pytest

from src.ui.callbacks.flushing_callbacks import (
    _nonnegative_number,
    _positive_number,
    parse_hydrant_ids,
)


def test_parse_hydrant_ids_accepts_supported_separators() -> None:
    assert parse_hydrant_ids("J1, J2\nJ3;J4") == [
        "J1",
        "J2",
        "J3",
        "J4",
    ]


@pytest.mark.parametrize(
    "value",
    [None, "", " \n , ; "],
)
def test_parse_hydrant_ids_rejects_empty_input(
    value: str | None,
) -> None:
    with pytest.raises(ValueError, match="at least one"):
        parse_hydrant_ids(value)


def test_parse_hydrant_ids_rejects_duplicates() -> None:
    with pytest.raises(ValueError, match="must be unique"):
        parse_hydrant_ids("J1, J2, J1")


@pytest.mark.parametrize(
    "value",
    [None, "invalid", 0, -1, float("inf")],
)
def test_positive_number_rejects_invalid_values(value) -> None:
    with pytest.raises(ValueError):
        _positive_number(value, "Test value")


@pytest.mark.parametrize(
    "value",
    [None, "invalid", -1, float("nan")],
)
def test_nonnegative_number_rejects_invalid_values(value) -> None:
    with pytest.raises(ValueError):
        _nonnegative_number(value, "Test value")


def test_numeric_validators_accept_valid_values() -> None:
    assert _positive_number(
        "0.002",
        "Area",
    ) == pytest.approx(0.002)

    assert _nonnegative_number(
        0,
        "Threshold",
    ) == pytest.approx(0.0)