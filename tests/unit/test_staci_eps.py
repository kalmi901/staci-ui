import json
import subprocess
from pathlib import Path

import pytest

from src.staci import eps


@pytest.fixture
def staci_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    executable = tmp_path / "staci.exe"
    executable.write_text("fake executable", encoding="utf-8")
    monkeypatch.setattr(eps, "STACI_EXECUTABLE", executable)
    monkeypatch.setattr(eps, "STACI_TIMEOUT_SECONDS", 17)
    return executable


def test_run_staci_eps_builds_command_and_collects_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    staci_executable: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    inp_path = run_dir / "network.inp"
    inp_path.write_text("[TITLE]\nTest network\n", encoding="utf-8")
    output_prefix = run_dir / "results"

    metadata = {
        "simulation": {"status": "complete", "frames": 3},
        "ranges": {"pressure_head": {"min": 10.0, "max": 20.0}},
    }
    output_prefix.with_suffix(".h5").touch()
    output_prefix.with_suffix(".meta.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="STACI stdout\n",
            stderr="STACI stderr\n",
        )

    monkeypatch.setattr(eps.subprocess, "run", fake_run)

    result = eps.run_staci_eps(inp_path, output_prefix)

    assert captured["command"] == [
        str(staci_executable),
        "--epanet-eps",
        str(inp_path.resolve()),
        "-o",
        str(output_prefix.resolve()),
    ]
    assert captured["kwargs"] == {
        "cwd": run_dir.resolve(),
        "capture_output": True,
        "text": True,
        "errors": "replace",
        "check": False,
        "timeout": 17,
    }
    assert result.returncode == 0
    assert result.h5_path == output_prefix.resolve().with_suffix(".h5")
    assert result.meta_path == output_prefix.resolve().with_suffix(".meta.json")
    assert result.meta == metadata
    assert result.stdout_path.read_text(encoding="utf-8") == "STACI stdout\n"
    assert result.stderr_path.read_text(encoding="utf-8") == "STACI stderr\n"


def test_run_staci_eps_rejects_missing_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_executable = tmp_path / "missing-staci.exe"
    monkeypatch.setattr(eps, "STACI_EXECUTABLE", missing_executable)

    with pytest.raises(FileNotFoundError, match="STACI executable not found"):
        eps.run_staci_eps(
            tmp_path / "network.inp",
            tmp_path / "results",
        )


def test_run_staci_eps_writes_partial_logs_on_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    staci_executable: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    inp_path = run_dir / "network.inp"
    output_prefix = run_dir / "results"

    def fake_run(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            command,
            timeout=17,
            output=b"partial stdout",
            stderr=b"partial \xffstderr",
        )

    monkeypatch.setattr(eps.subprocess, "run", fake_run)

    with pytest.raises(TimeoutError, match="17 s timeout"):
        eps.run_staci_eps(inp_path, output_prefix)

    assert (run_dir / "staci.stdout.log").read_text(
        encoding="utf-8"
    ) == "partial stdout"
    assert (run_dir / "staci.stderr.log").read_text(
        encoding="utf-8"
    ) == "partial \ufffdstderr"