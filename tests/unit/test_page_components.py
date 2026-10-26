from src.ui.pages.components import (
    round_color_range_value,
)


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
    assert round_color_range_value(
        "head",
        None,
    ) is None