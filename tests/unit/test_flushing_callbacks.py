import pytest

from src.ui.callbacks.flushing_callbacks import (
    _nonnegative_number,
    _positive_number,
    parse_hydrant_ids,
)

from src.ui.pages.flushing_analysis import (
    make_flushing_scenario_options,
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
    

def test_make_flushing_scenario_options_uses_plan_order() -> None:
    options, selected = (
        make_flushing_scenario_options(
            {
                "mode": "single",
                "plan": [
                    {
                        "rank": "1",
                        "node_id": "J2",
                    },
                    {
                        "rank": "2",
                        "node_id": "J1",
                    },
                ],
            }
        )
    )

    assert options == [
        {
            "label": "#1 · J2",
            "value": "J2",
        },
        {
            "label": "#2 · J1",
            "value": "J1",
        },
    ]
    assert selected == "J2"


def test_make_flushing_scenario_options_handles_multi_mode() -> None:
    options, selected = (
        make_flushing_scenario_options(
            {
                "mode": "multi",
                "plan": [
                    {
                        "rank": "1",
                        "node_id": '["J1","J2"]',
                    }
                ],
            }
        )
    )

    assert options == [
        {
            "label": "Combined hydrant scenario",
            "value": "multi",
        }
    ]
    assert selected == "multi"
