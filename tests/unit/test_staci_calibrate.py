import json
import os
import subprocess
from pathlib import Path

import pytest

from src.staci import calibrate


@pytest.fixture
def calibrate_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    executable = tmp_path / "staci_calibrate.exe"
    executable.write_text(
        "fake executable",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        calibrate,
        "STACI_CALIBRATE_EXECUTABLE",
        executable,
    )
    monkeypatch.setattr(
        calibrate,
        "STACI_TIMEOUT_SECONDS",
        31,
    )

    return executable


def _create_settings(
    tmp_path: Path,
) -> tuple[Path, Path]:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    for index in range(2):
        (run_dir / f"network_{index}.inp").write_text(
            "[END]\n",
            encoding="utf-8",
        )

    measurements_path = run_dir / "calibrate_targets.json"
    measurements_path.write_text(
        json.dumps(
            {
                "measurements": [
                    {
                        "id": "NODE64",
                        "type": "node",
                        "values": [1.0, 1.1],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    settings_path = run_dir / "staci_calibrate_settings.json"

    calibrate.write_calibrate_settings(
        settings_path,
        measurements_path=measurements_path,
        snapshot_count=2,
        overrides={
            "popsize": 4,
            "ngen": 1,
        },
    )

    return run_dir, settings_path


def test_write_calibrate_settings_writes_expected_json(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    for index in range(2):
        (run_dir / f"network_{index}.inp").write_text(
            "[END]\n",
            encoding="utf-8",
        )

    measurements_path = run_dir / "targets.json"
    measurements_path.write_text(
        '{"measurements": []}',
        encoding="utf-8",
    )
    settings_path = (
        run_dir / "staci_calibrate_settings.json"
    )

    calibrate.write_calibrate_settings(
        settings_path,
        measurements_path=measurements_path,
        snapshot_count=2,
        overrides={
            "type_of_pipe_selection": "most_sensitive",
            "num_of_active_pipes": 7,
            "popsize": 8,
            "ngen": 10,
        },
    )

    settings = json.loads(
        settings_path.read_text(encoding="utf-8")
    )

    assert settings["dir_name"] == (
        str(run_dir.resolve()) + os.sep
    )
    assert settings["sollwert_dfile"] == "targets.json"
    assert settings["fname_prefix"] == "network_"
    assert settings["network_extension"] == ".inp"
    assert settings["Start_of_Periods"] == 0
    assert settings["Num_of_Periods"] == 2
    assert settings["type_of_pipe_selection"] == (
        "most_sensitive"
    )
    assert settings["num_of_active_pipes"] == 7
    assert settings["popsize"] == 8
    assert settings["ngen"] == 10
    assert "network_file" not in settings
    assert "Dmin" not in settings


def test_write_calibrate_settings_handles_dmin_selection(
    tmp_path: Path,
) -> None:
    for index in range(2):
        (tmp_path / f"network_{index}.inp").write_text(
            "[END]\n",
            encoding="utf-8",
        )

    measurements_path = tmp_path / "targets.json"
    measurements_path.write_text(
        '{"measurements": []}',
        encoding="utf-8",
    )
    settings_path = (
        tmp_path / "staci_calibrate_settings.json"
    )

    calibrate.write_calibrate_settings(
        settings_path,
        measurements_path=measurements_path,
        snapshot_count=2,
        overrides={
            "type_of_pipe_selection": "Dmin",
            "Dmin": 0.15,
        },
    )

    settings = json.loads(
        settings_path.read_text(encoding="utf-8")
    )

    assert settings["Dmin"] == 0.15
    assert "num_of_active_pipes" not in settings
    assert "pipe_ids" not in settings


def test_run_staci_calibrate_builds_command_and_collects_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    calibrate_executable: Path,
) -> None:
    run_dir, settings_path = _create_settings(tmp_path)
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs

        for filename in (
            "best.dat",
            "bog.dat",
            "sensitivity_MassFlowRates.dat",
            "sensitivity_Pressures.dat",
            "calibrate.log",
            "calibrate-best.log",
            "staci-diagnostics.jsonl",
        ):
            (run_dir / filename).touch()

        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="calibrate stdout\n",
            stderr="calibrate stderr\n",
        )

    monkeypatch.setattr(
        calibrate.subprocess,
        "run",
        fake_run,
    )

    result = calibrate.run_staci_calibrate(
        settings_path,
        seed=12345,
    )

    assert captured["command"] == [
        str(calibrate_executable),
        "--settings",
        str(settings_path.resolve()),
        "--seed",
        "12345",
        "--diagnostics-file",
        str(run_dir / "staci-diagnostics.jsonl"),
    ]
    assert captured["kwargs"] == {
        "cwd": run_dir.resolve(),
        "capture_output": True,
        "text": True,
        "errors": "replace",
        "check": False,
        "timeout": 31,
    }

    assert result.returncode == 0
    assert result.success is True
    assert result.best_data_path == run_dir / "best.dat"
    assert result.history_path == run_dir / "bog.dat"
    assert result.stdout_path.read_text(
        encoding="utf-8"
    ) == "calibrate stdout\n"
    assert result.stderr_path.read_text(
        encoding="utf-8"
    ) == "calibrate stderr\n"


def test_run_staci_calibrate_is_not_successful_without_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    calibrate_executable: Path,
) -> None:
    _run_dir, settings_path = _create_settings(tmp_path)

    monkeypatch.setattr(
        calibrate.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="",
            stderr="",
        ),
    )

    result = calibrate.run_staci_calibrate(settings_path)

    assert result.returncode == 0
    assert result.success is False


def test_run_staci_calibrate_rejects_missing_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        calibrate,
        "STACI_CALIBRATE_EXECUTABLE",
        tmp_path / "missing-calibrate.exe",
    )

    with pytest.raises(
        FileNotFoundError,
        match="executable not found",
    ):
        calibrate.run_staci_calibrate(
            tmp_path / "staci_calibrate_settings.json"
        )


def test_run_staci_calibrate_writes_partial_logs_on_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    calibrate_executable: Path,
) -> None:
    run_dir, settings_path = _create_settings(tmp_path)

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            command,
            timeout=31,
            output=b"partial calibrate stdout",
            stderr=b"partial calibrate \xffstderr",
        )

    monkeypatch.setattr(
        calibrate.subprocess,
        "run",
        fake_run,
    )

    with pytest.raises(
        TimeoutError,
        match="31 s timeout",
    ):
        calibrate.run_staci_calibrate(settings_path)

    assert (
        run_dir / "staci_calibrate.stdout.log"
    ).read_text(
        encoding="utf-8"
    ) == "partial calibrate stdout"

    assert (
        run_dir / "staci_calibrate.stderr.log"
    ).read_text(
        encoding="utf-8"
    ) == "partial calibrate \ufffdstderr"


def test_run_staci_calibrate_wraps_process_start_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    calibrate_executable: Path,
) -> None:
    _run_dir, settings_path = _create_settings(tmp_path)

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise OSError("process could not start")

    monkeypatch.setattr(
        calibrate.subprocess,
        "run",
        fake_run,
    )

    with pytest.raises(
        RuntimeError,
        match="OSError: process could not start",
    ):
        calibrate.run_staci_calibrate(settings_path)

def test_write_calibrate_settings_handles_explicit_pipe_list(
    tmp_path: Path,
) -> None:
    measurements_path = tmp_path / "measurements.json"
    measurements_path.write_text(
        '{"measurements": []}',
        encoding="utf-8",
    )

    for index in range(2):
        (tmp_path / f"network_{index}.inp").touch()

    settings_path = tmp_path / "settings.json"

    calibrate.write_calibrate_settings(
        settings_path,
        measurements_path=measurements_path,
        snapshot_count=2,
        overrides={
            "type_of_pipe_selection": "list",
            "pipe_ids": ["Small", "Large"],
            "min_diameter_m": 0.05,
            "max_diameter_m": 0.30,
        },
    )

    settings = json.loads(
        settings_path.read_text(encoding="utf-8")
    )

    assert settings["pipe_ids"] == ["Small", "Large"]
    assert settings["min_diameter_m"] == 0.05
    assert settings["max_diameter_m"] == 0.30
    assert "num_of_active_pipes" not in settings
    assert "Dmin" not in settings


def test_write_calibrate_settings_handles_all_pipes(
    tmp_path: Path,
) -> None:
    measurements_path = tmp_path / "measurements.json"
    measurements_path.write_text(
        '{"measurements": []}',
        encoding="utf-8",
    )
    (tmp_path / "network_0.inp").touch()

    settings_path = tmp_path / "settings.json"

    calibrate.write_calibrate_settings(
        settings_path,
        measurements_path=measurements_path,
        snapshot_count=1,
        overrides={
            "type_of_pipe_selection": "all",
        },
    )

    settings = json.loads(
        settings_path.read_text(encoding="utf-8")
    )

    assert settings["type_of_pipe_selection"] == "all"
    assert "pipe_ids" not in settings
    assert "num_of_active_pipes" not in settings
    assert "Dmin" not in settings

@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [
        (0.0, 0.3),
        (-0.1, 0.3),
        (0.3, 0.3),
        (0.4, 0.3),
        (float("nan"), 0.3),
        (0.1, float("inf")),
    ],
)
def test_write_calibrate_settings_rejects_invalid_bounds(
    tmp_path: Path,
    minimum: float,
    maximum: float,
) -> None:
    measurements_path = tmp_path / "measurements.json"
    measurements_path.write_text(
        '{"measurements": []}',
        encoding="utf-8",
    )
    (tmp_path / "network_0.inp").touch()

    with pytest.raises(ValueError):
        calibrate.write_calibrate_settings(
            tmp_path / "settings.json",
            measurements_path=measurements_path,
            snapshot_count=1,
            overrides={
                "min_diameter_m": minimum,
                "max_diameter_m": maximum,
            },
        )
