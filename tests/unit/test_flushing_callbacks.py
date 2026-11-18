import pytest

from src.ui.callbacks.flushing_callbacks import parse_hydrant_ids
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


def test_make_flushing_scenario_options_uses_plan_order() -> None:
    options, selected = make_flushing_scenario_options(
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
    options, selected = make_flushing_scenario_options(
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

    assert options == [
        {
            "label": "Combined hydrant scenario",
            "value": "multi",
        }
    ]
    assert selected == "multi"
