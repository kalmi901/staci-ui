from pathlib import Path

import pytest

from src.results.calibration import (
    parse_calibration_best,
    parse_calibration_history,
)

def test_parse_calibration_best_returns_pipes_and_comparisons(
    tmp_path: Path,
) -> None:
    path = tmp_path / "best.dat"
    path.write_text(
        "\n".join(
            [
                "Small ; Large ;",
                "1.10000e-01 ; 2.10000e-01 ;",
                "1.10000e+00 ; 1.05000e+00 ;",
                (
                    "Sollwert J1 ; J1 ; "
                    "Sollwert T1 ; T1 ;"
                ),
                (
                    "3.03000e+01 ; 3.02000e+01 ; "
                    "3.00000e+01 ; 3.00000e+01 ;"
                ),
                (
                    "3.02000e+01 ; 3.01000e+01 ; "
                    "3.01000e+01 ; 3.00900e+01 ;"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = parse_calibration_best(path)

    assert [pipe.pipe_id for pipe in result.pipes] == [
        "Small",
        "Large",
    ]
    assert result.pipes[0].diameter_m == pytest.approx(0.11)
    assert result.pipes[1].diameter_ratio == pytest.approx(1.05)

    assert len(result.comparisons) == 4
    assert result.comparisons[0].period_index == 0
    assert result.comparisons[0].measurement_id == "J1"
    assert result.comparisons[0].measured_value == pytest.approx(
        30.3
    )
    assert result.comparisons[0].computed_value == pytest.approx(
        30.2
    )


def test_parse_calibration_history_returns_optimizer_log(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bog.dat"
    path.write_text(
        "1;6;1.25000e-02;3.00000e-03;\n"
        "10;60;2.50000e-03;1.00000e-03;\n",
        encoding="utf-8",
    )

    history = parse_calibration_history(path)

    assert len(history) == 2
    assert history[0].generation == 1
    assert history[0].function_evaluations == 6
    assert history[0].best_objective == pytest.approx(0.0125)
    assert history[1].improvement == pytest.approx(0.001)


@pytest.mark.parametrize(
    "content",
    [
        "",
        "Pipe1;\n0.1;\n1.0;\n",
        (
            "Pipe1;Pipe2;\n"
            "0.1;\n"
            "1.0;1.0;\n"
            "Sollwert J1;J1;\n"
            "10.0;10.0;\n"
        ),
    ],
)
def test_parse_calibration_best_rejects_malformed_results(
    tmp_path: Path,
    content: str,
) -> None:
    path = tmp_path / "best.dat"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        parse_calibration_best(path)


def test_parse_calibration_history_rejects_invalid_row(
    tmp_path: Path,
) -> None:
    path = tmp_path / "bog.dat"
    path.write_text(
        "1;10;not-a-number;0.0;\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        parse_calibration_history(path)