from pathlib import Path

from src.staci.error_messages import (
    format_staci_failure,
)


def test_format_staci_failure_uses_stderr_errors(
    tmp_path: Path,
) -> None:
    stderr_path = tmp_path / "stderr.log"
    stdout_path = tmp_path / "stdout.log"

    stderr_path.write_text(
        (
            "WARNING [EPANET]: ignored warning\n"
            "ERROR [staci_flush][INPUT.CONFIG]: "
            "Unknown hydrant node J999.\n"
        ),
        encoding="utf-8",
    )
    stdout_path.write_text(
        "!!!ERROR!!! stdout error\n",
        encoding="utf-8",
    )

    message = format_staci_failure(
        "STACI Flush",
        2,
        stderr_path=stderr_path,
        stdout_path=stdout_path,
    )

    assert "return code 2" in message
    assert "Unknown hydrant node J999" in message
    assert "WARNING" not in message
    assert "stdout error" not in message


def test_format_staci_failure_falls_back_to_stdout(
    tmp_path: Path,
) -> None:
    stderr_path = tmp_path / "stderr.log"
    stdout_path = tmp_path / "stdout.log"

    stderr_path.write_text(
        "WARNING [EPANET]: compatibility warning\n",
        encoding="utf-8",
    )
    stdout_path.write_text(
        ("Building system...\n!!!ERROR!!! edge 10 and node 10 have the same ID!\n"),
        encoding="utf-8",
    )

    message = format_staci_failure(
        "STACI Split",
        -1,
        stderr_path=stderr_path,
        stdout_path=stdout_path,
    )

    assert "return code -1" in message
    assert "have the same ID" in message
    assert "WARNING" not in message


def test_format_staci_failure_has_generic_fallback(
    tmp_path: Path,
) -> None:
    stderr_path = tmp_path / "stderr.log"
    stderr_path.write_text("", encoding="utf-8")

    assert (
        format_staci_failure(
            "STACI EPS",
            1,
            stderr_path=stderr_path,
        )
        == "STACI EPS failed (return code 1)."
    )


def test_format_staci_failure_prefers_structured_error(
    tmp_path: Path,
) -> None:
    stderr_path = tmp_path / "stderr.log"

    stderr_path.write_text(
        (
            "ERROR [staci_split][LEGACY_ERROR]: "
            "ERROR in Load_Settings() unknown obj_type >None<\n"
            "ERROR [staci_split][INPUT_OR_CONFIGURATION]: "
            "/build/staci/src/staci_split.cpp:1756: "
            "Application stopped. Context:\n"
            "\n"
            "ERROR in Load_Settings() unknown obj_type >None<\n"
        ),
        encoding="utf-8",
    )

    message = format_staci_failure(
        "STACI Split",
        2,
        stderr_path=stderr_path,
    )

    assert message == (
        "STACI Split failed (return code 2). "
        "ERROR in Load_Settings() unknown obj_type >None<"
    )
    assert "/build/staci" not in message
