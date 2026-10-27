import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services import calibration_runner, run_storage
from src.staci.calibrate import StaciCalibrateResults


RUN_ID = "123456abcdef"


@pytest.fixture
def run_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    root = tmp_path / "runs"

    monkeypatch.setattr(
        calibration_runner,
        "RUN_ROOT",
        root,
    )
    monkeypatch.setattr(
        run_storage,
        "RUN_ROOT",
        root,
    )
    monkeypatch.setattr(
        calibration_runner.uuid,
        "uuid4",
        lambda: SimpleNamespace(
            hex=f"{RUN_ID}ffff"
        ),
    )

    return root


@pytest.fixture
def snapshots(tmp_path: Path) -> list[Path]:
    paths = [
        tmp_path / "period-a.inp",
        tmp_path / "period-b.inp",
    ]

    for path in paths:
        path.write_text(
            "[TITLE]\nCalibration unit test\n[END]\n",
            encoding="utf-8",
        )

    return paths


def _network_state(
    *,
    end_node: str = "T1",
) -> dict:
    return {
        "nodes": {
            "id": ["R1", "J1", "T1"],
            "type": [
                "Reservoir",
                "Junction",
                "Tank",
            ],
        },
        "links": {
            "id": ["Small", "Large"],
            "type": ["Pipe", "Pipe"],
            "start_node": ["R1", "J1"],
            "end_node": ["J1", end_node],
        },
    }


def _result(run_dir: Path, returncode: int = 0):
    return StaciCalibrateResults(
        returncode=returncode,
        stdout_path=run_dir / "staci_calibrate.stdout.log",
        stderr_path=run_dir / "staci_calibrate.stderr.log",
        diagnostics_path=run_dir / "staci-diagnostics.jsonl",
        calibration_log_path=run_dir / "calibrate.log",
        best_log_path=run_dir / "calibrate-best.log",
        best_data_path=run_dir / "best.dat",
        history_path=run_dir / "bog.dat",
        sensitivity_mass_flow_path=(
            run_dir / "sensitivity_MassFlowRates.dat"
        ),
        sensitivity_pressure_path=(
            run_dir / "sensitivity_Pressures.dat"
        ),
    )


def test_call_staci_calibrate_service_persists_inputs_and_results(
    snapshots: list[Path],
    run_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = run_root / "calibration" / RUN_ID
    logged: dict[str, object] = {}

    monkeypatch.setattr(
        calibration_runner,
        "read_water_network_model",
        lambda path: _network_state(),
    )

    def fake_log_prepared_input(
        inp_path,
        run_id,
        **kwargs,
    ):
        logged["inp_path"] = inp_path
        logged["run_id"] = run_id
        logged.update(kwargs)

    monkeypatch.setattr(
        calibration_runner,
        "log_prepared_input",
        fake_log_prepared_input,
    )

    def fake_run(settings_path: Path, *, seed: int):
        assert settings_path == (
            run_dir / "staci_calibrate_settings.json"
        )
        assert seed == 12345

        (run_dir / "best.dat").write_text(
            "Large ;\n"
            "2.10000e-01 ;\n"
            "1.05000e+00 ;\n"
            "Sollwert J1 ; J1 ;\n"
            "3.03000e+01 ; 3.02000e+01 ;\n"
            "3.02000e+01 ; 3.01000e+01 ;\n",
            encoding="utf-8",
        )
        (run_dir / "bog.dat").write_text(
            "1;6;1.25000e-02;3.00000e-03;\n",
            encoding="utf-8",
        )

        for filename in (
            "staci_calibrate.stdout.log",
            "staci_calibrate.stderr.log",
            "staci-diagnostics.jsonl",
            "calibrate.log",
            "calibrate-best.log",
            "sensitivity_MassFlowRates.dat",
            "sensitivity_Pressures.dat",
        ):
            (run_dir / filename).touch()

        return _result(run_dir)

    monkeypatch.setattr(
        calibration_runner,
        "run_staci_calibrate",
        fake_run,
    )

    state = (
        calibration_runner.call_staci_calibrate_service(
            snapshots,
            measurements={
                "measurements": [
                    {
                        "id": "J1",
                        "type": "node",
                        "values": [30.3, 30.2],
                    }
                ]
            },
            optimizer_settings={
                "type_of_pipe_selection": "list",
                "pipe_ids": ["Large"],
                "popsize": 6,
                "ngen": 10,
            },
            seed=12345,
        )
    )

    assert (
        run_dir / "network_0.inp"
    ).read_bytes() == snapshots[0].read_bytes()
    assert (
        run_dir / "network_1.inp"
    ).read_bytes() == snapshots[1].read_bytes()

    settings = json.loads(
        (
            run_dir / "staci_calibrate_settings.json"
        ).read_text(encoding="utf-8")
    )
    assert settings["Num_of_Periods"] == 2
    assert settings["network_extension"] == ".inp"
    assert settings["pipe_ids"] == ["Large"]

    assert state["run_id"] == RUN_ID
    assert state["summary"]["snapshot_count"] == 2
    assert state["summary"]["measurement_count"] == 1
    assert state["summary"]["calibrated_pipe_count"] == 1
    assert state["summary"]["comparison_count"] == 2
    assert state["files"]["best"] == "best.dat"
    assert state["pipes"][0]["pipe_id"] == "Large"

    assert logged["run_id"] == RUN_ID
    assert logged["inp_path"] == (
        run_dir / "network_0.inp"
    )

    saved_state = json.loads(
        (run_dir / "run.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved_state == state

def test_call_staci_calibrate_service_rejects_topology_mismatch(
    snapshots: list[Path],
    run_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_read(path: Path):
        if Path(path).name == "period-a.inp":
            return _network_state()

        return _network_state(end_node="J1")

    monkeypatch.setattr(
        calibration_runner,
        "read_water_network_model",
        fake_read,
    )

    with pytest.raises(
        ValueError,
        match="topologically compatible",
    ):
        calibration_runner.call_staci_calibrate_service(
            snapshots,
            measurements={
                "measurements": [
                    {
                        "id": "J1",
                        "type": "node",
                        "values": [30.3, 30.2],
                    }
                ]
            },
        )

    assert not (
        run_root / "calibration" / RUN_ID
    ).exists()

def test_call_staci_calibrate_service_rejects_measurement_count(
    snapshots: list[Path],
    run_root: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="exactly 2 values",
    ):
        calibration_runner.call_staci_calibrate_service(
            snapshots,
            measurements={
                "measurements": [
                    {
                        "id": "J1",
                        "type": "node",
                        "values": [30.3],
                    }
                ]
            },
        )

def test_call_staci_calibrate_service_rejects_failed_run(
    snapshots: list[Path],
    run_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_dir = run_root / "calibration" / RUN_ID

    monkeypatch.setattr(
        calibration_runner,
        "read_water_network_model",
        lambda path: _network_state(),
    )
    monkeypatch.setattr(
        calibration_runner,
        "log_prepared_input",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        calibration_runner,
        "run_staci_calibrate",
        lambda settings_path, seed: _result(
            run_dir,
            returncode=2,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="return code 2",
    ):
        calibration_runner.call_staci_calibrate_service(
            snapshots,
            measurements={
                "measurements": [
                    {
                        "id": "J1",
                        "type": "node",
                        "values": [30.3, 30.2],
                    }
                ]
            },
        )


def test_load_calibration_run_returns_manifest(
    run_root: Path,
) -> None:
    run_dir = run_root / "calibration" / RUN_ID
    run_dir.mkdir(parents=True)

    expected = {
        "run_id": RUN_ID,
        "status": "success",
    }

    (run_dir / "run.json").write_text(
        json.dumps(expected),
        encoding="utf-8",
    )

    assert (
        calibration_runner.load_calibration_run(RUN_ID)
        == expected
    )

