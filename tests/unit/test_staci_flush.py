import json
import subprocess
from pathlib import Path

import pytest

from src.staci import flush


@pytest.fixture
def flush_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    executable = tmp_path / "staci_flush.exe"
    executable.write_text("fake executable", encoding="utf-8")
    monkeypatch.setattr(flush, "STACI_FLUSH_EXECUTABLE", executable)
    monkeypatch.setattr(flush, "STACI_TIMEOUT_SECONDS", 29)
    return executable


def _create_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    inp_path = run_dir / "network.inp"
    inp_path.write_text("[TITLE]\nTest network\n", encoding="utf-8")
    config_path = run_dir / "flushing_config.json"
    output_dir = run_dir / "results"

    flush.write_flush_config(
        config_path,
        hydrant_node_ids=["J1", "J2"],
        hydrant_area_m2=0.002,
        total_loss_coefficient=2.0,
        velocity_threshold_mps=0.5,
        output_dir="results",
        min_pressure_head_m=1.5,
        write_network_files=True,
    )

    return inp_path, config_path, output_dir


def test_write_flush_config_writes_expected_json(tmp_path: Path) -> None:
    config_path = tmp_path / "flushing_config.json"

    flush.write_flush_config(
        config_path,
        hydrant_node_ids=["J1", "J2"],
        hydrant_area_m2=0.002,
        total_loss_coefficient=2.0,
        velocity_threshold_mps=0.5,
        output_dir="results/flushing",
        mode="multi",
        min_pressure_head_m=3.0,
        write_network_files=True,
    )

    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "mode": "multi",
        "hydrant_node_ids": ["J1", "J2"],
        "hydrant_area_m2": 0.002,
        "total_loss_coefficient": 2.0,
        "velocity_threshold_mps": 0.5,
        "min_pressure_head_m": 3.0,
        "output_dir": "results/flushing",
        "write_network_files": True,
    }


def test_run_staci_flush_builds_command_and_collects_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flush_executable: Path,
) -> None:
    inp_path, config_path, output_dir = _create_inputs(tmp_path)
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs

        output_dir.mkdir()
        for filename in (
            "run.json",
            "scenarios.csv",
            "flushing_plan.csv",
            "flushing_plan.txt",
            "pipe_travel_times.csv",
            "pipes_above_threshold.csv",
            "pipe_coverage.csv",
            "scenario_hydrants.csv",
            "scenario_pipes.csv",
        ):
            (output_dir / filename).touch()

        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="flush stdout\n",
            stderr="flush stderr\n",
        )

    monkeypatch.setattr(flush.subprocess, "run", fake_run)

    result = flush.run_staci_flush(inp_path, config_path)

    assert captured["command"] == [
        str(flush_executable),
        "--inp",
        str(inp_path.resolve()),
        "--config",
        str(config_path.resolve()),
    ]
    assert captured["kwargs"] == {
        "cwd": config_path.parent.resolve(),
        "capture_output": True,
        "text": True,
        "errors": "replace",
        "check": False,
        "timeout": 29,
    }
    assert result.returncode == 0
    assert result.output_dir == output_dir.resolve()
    assert result.success is True
    assert result.partial is False
    assert result.plan_csv_path == (
        output_dir.resolve() / "flushing_plan.csv"
    )
    assert result.stdout_path.read_text(
        encoding="utf-8"
    ) == "flush stdout\n"
    assert result.stderr_path.read_text(
        encoding="utf-8"
    ) == "flush stderr\n"
    assert result.scenario_hydrants_path == (
        output_dir.resolve()
        / "scenario_hydrants.csv"
    )

    assert result.scenario_pipes_path == (
        output_dir.resolve()
        / "scenario_pipes.csv"
    )


def test_run_staci_flush_recognizes_partial_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flush_executable: Path,
) -> None:
    inp_path, config_path, output_dir = _create_inputs(tmp_path)

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        output_dir.mkdir()
        (output_dir / "run.json").touch()
        (output_dir / "scenarios.csv").touch()

        return subprocess.CompletedProcess(
            command,
            returncode=3,
            stdout="partial results\n",
            stderr="invalid scenario\n",
        )

    monkeypatch.setattr(flush.subprocess, "run", fake_run)

    result = flush.run_staci_flush(inp_path, config_path)

    assert result.returncode == 3
    assert result.success is False
    assert result.partial is True


def test_run_staci_flush_rejects_missing_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_executable = tmp_path / "missing-staci-flush.exe"
    monkeypatch.setattr(
        flush,
        "STACI_FLUSH_EXECUTABLE",
        missing_executable,
    )

    with pytest.raises(FileNotFoundError, match="executable not found"):
        flush.run_staci_flush(
            tmp_path / "network.inp",
            tmp_path / "flushing_config.json",
        )


def test_run_staci_flush_rejects_missing_config(
    tmp_path: Path,
    flush_executable: Path,
) -> None:
    inp_path = tmp_path / "network.inp"
    inp_path.write_text("[TITLE]\n", encoding="utf-8")

    with pytest.raises(
        FileNotFoundError,
        match="configuration file not found",
    ):
        flush.run_staci_flush(
            inp_path,
            tmp_path / "missing-config.json",
        )


def test_run_staci_flush_writes_partial_logs_on_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flush_executable: Path,
) -> None:
    inp_path, config_path, _output_dir = _create_inputs(tmp_path)

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            command,
            timeout=29,
            output=b"partial flush stdout",
            stderr=b"partial flush \xffstderr",
        )

    monkeypatch.setattr(flush.subprocess, "run", fake_run)

    with pytest.raises(TimeoutError, match="29 s timeout"):
        flush.run_staci_flush(inp_path, config_path)

    assert (
        config_path.parent / "staci_flush.stdout.log"
    ).read_text(encoding="utf-8") == "partial flush stdout"

    assert (
        config_path.parent / "staci_flush.stderr.log"
    ).read_text(encoding="utf-8") == "partial flush \ufffdstderr"


def test_run_staci_flush_wraps_process_start_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    flush_executable: Path,
) -> None:
    inp_path, config_path, _output_dir = _create_inputs(tmp_path)

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise OSError("process could not start")

    monkeypatch.setattr(flush.subprocess, "run", fake_run)

    with pytest.raises(
        RuntimeError,
        match="OSError: process could not start",
    ):
        flush.run_staci_flush(inp_path, config_path)
