import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.staci import split


@pytest.fixture
def split_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    executable = tmp_path / "staci_split.exe"
    executable.write_text("fake executable", encoding="utf-8")
    monkeypatch.setattr(split, "STACI_SPLIT_EXECUTABLE", executable)
    monkeypatch.setattr(split, "STACI_TIMEOUT_SECONDS", 23)
    return executable


def test_write_split_settings_writes_defaults_and_overrides(
    tmp_path: Path,
) -> None:
    inp_path = tmp_path / "network.inp"
    settings_path = tmp_path / "staci_split_settings.xml"

    split.write_split_settings(
        settings_path,
        inp_path=inp_path,
        overrides={
            "n_comm": 5,
            "weight_type": "dp",
            "popsize": 8,
        },
    )

    root = ET.parse(settings_path).getroot()
    values = {element.tag: element.text for element in root}

    assert root.tag == "settings"
    assert values == {
        "fname": str(inp_path.resolve()),
        "global_debug_level": "1",
        "n_comm": "5",
        "weight_type": "dp",
        "weight_type_mod": "diameter",
        "logfilename": "split.log",
        "obj_type": "modularity",
        "popsize": "8",
        "ngen": "50",
        "pmut": "0.25",
        "pcross": "0.8",
    }


def test_run_staci_split_builds_command_and_collects_membership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    split_executable: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    inp_path = run_dir / "model.inp"
    inp_path.write_text("[TITLE]\nTest network\n", encoding="utf-8")
    settings_path = run_dir / "staci_split_settings.xml"
    settings_path.write_text("<settings />", encoding="utf-8")
    membership_path = run_dir / "membership.txt"

    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        membership_path.write_text(
            "n_nodes : 1\n#0; J1;\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="split stdout\n",
            stderr="split stderr\n",
        )

    monkeypatch.setattr(split.subprocess, "run", fake_run)

    result = split.run_staci_split(
        inp_path,
        settings_path,
        seed=12345,
    )

    assert captured["command"] == [
        str(split_executable),
        "--seed",
        "12345",
    ]
    assert captured["kwargs"] == {
        "cwd": run_dir.resolve(),
        "capture_output": True,
        "text": True,
        "errors": "replace",
        "check": False,
        "timeout": 23,
    }
    assert result.returncode == 0
    assert result.timed_out is False
    assert result.membership_path == membership_path
    assert result.success is True
    assert result.stdout_path.read_text(encoding="utf-8") == "split stdout\n"
    assert result.stderr_path.read_text(encoding="utf-8") == "split stderr\n"


def test_run_staci_split_is_not_successful_without_membership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    split_executable: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    inp_path = run_dir / "model.inp"
    settings_path = run_dir / "staci_split_settings.xml"
    settings_path.write_text("<settings />", encoding="utf-8")

    monkeypatch.setattr(
        split.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="",
            stderr="",
        ),
    )

    result = split.run_staci_split(inp_path, settings_path)

    assert result.returncode == 0
    assert result.membership_path is None
    assert result.success is False


def test_run_staci_split_rejects_missing_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_executable = tmp_path / "missing-staci-split.exe"
    monkeypatch.setattr(split, "STACI_SPLIT_EXECUTABLE", missing_executable)

    with pytest.raises(FileNotFoundError, match="STACI_SPLIT executable not found"):
        split.run_staci_split(
            tmp_path / "model.inp",
            tmp_path / "staci_split_settings.xml",
        )


def test_run_staci_split_rejects_unexpected_settings_path(
    tmp_path: Path,
    split_executable: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    inp_path = run_dir / "model.inp"
    unexpected_settings_path = run_dir / "other_settings.xml"
    unexpected_settings_path.write_text("<settings />", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid STACI Split settings path"):
        split.run_staci_split(inp_path, unexpected_settings_path)


def test_run_staci_split_rejects_missing_settings_file(
    tmp_path: Path,
    split_executable: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    inp_path = run_dir / "model.inp"
    settings_path = run_dir / "staci_split_settings.xml"

    with pytest.raises(FileNotFoundError, match="settings file not found"):
        split.run_staci_split(inp_path, settings_path)


def test_run_staci_split_writes_partial_logs_on_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    split_executable: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    inp_path = run_dir / "model.inp"
    settings_path = run_dir / "staci_split_settings.xml"
    settings_path.write_text("<settings />", encoding="utf-8")

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            command,
            timeout=23,
            output=b"partial split stdout",
            stderr=b"partial split \xffstderr",
        )

    monkeypatch.setattr(split.subprocess, "run", fake_run)

    with pytest.raises(TimeoutError, match="23 s timeout"):
        split.run_staci_split(inp_path, settings_path)

    assert (run_dir / "staci_split.stdout.log").read_text(
        encoding="utf-8"
    ) == "partial split stdout"
    assert (run_dir / "staci_split.stderr.log").read_text(
        encoding="utf-8"
    ) == "partial split \ufffdstderr"


def test_run_staci_split_wraps_process_start_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    split_executable: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    inp_path = run_dir / "model.inp"
    settings_path = run_dir / "staci_split_settings.xml"
    settings_path.write_text("<settings />", encoding="utf-8")

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise OSError("process could not start")

    monkeypatch.setattr(split.subprocess, "run", fake_run)

    with pytest.raises(
        RuntimeError,
        match="OSError: process could not start",
    ):
        split.run_staci_split(inp_path, settings_path)