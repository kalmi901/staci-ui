"""Verify real Dash-to-Celery context transfer using an isolated in-memory backend."""

import json
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from celery import Celery
from dash import CeleryManager

from app import app
from src.background_jobs import background_callback_manager, setup_worker_logging
from src.logging_setup import configure_logging
from src.run_logging import execution_id
from src.ui.callbacks import flushing_callbacks, hydraulic_callbacks
from tests.test_run_callbacks import CallbackRegistry


@contextmanager
def _fake_running_solver_job(
    request_state,
    *,
    workflow,
):
    assert workflow == "hydraulic"

    execution = SimpleNamespace(
        complete=lambda: None,
    )

    yield execution, request_state["payload"]


@pytest.mark.skipif(
    os.name != "posix",
    reason="Application file logging uses POSIX flock",
)
def test_background_task_preserves_verified_user_and_run_context(tmp_path, monkeypatch):
    old_handlers = logging.root.handlers[:]
    old_level = logging.root.level
    monkeypatch.setenv("STACI_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("STACI_LOG_READER_GID", "")
    configure_logging()
    try:
        # Capture the exact context Dash constructs from the HTTP request.
        key, callback = next(
            (key, value)
            for key, value in app.callback_map.items()
            if "hyd-run-store.data" in key and "hyd-run-status.children" in key
        )
        model = {"model_id": "abcdef123456", "filename": "same.inp"}
        payload = {
            "network_state": model,
            "backend": "wntr",
            "override_enabled": False,
            "duration": 1,
            "hydraulic_timestep": 5,
            "report_timestep": 60,
            "rule_timestep": 5,
            "demand_multiplier": 1.0,
        }
        requests_and_contexts = []
        for user_id in ("7", "8"):
            request_state = {
                "token": f"token-{user_id}",
                "workflow": "hydraulic",
                "payload": payload,
            }
            body = {
                "output": key,
                "outputs": [
                    {
                        "id": item.component_id,
                        "property": item.component_property,
                    }
                    for item in callback["output"]
                ],
                "inputs": [
                    dict(
                        callback["inputs"][0],
                        value=request_state,
                    )
                ],
                "state": [],
                "changedPropIds": ["hyd-job-request-store.data"],
            }
            with (
                patch.object(
                    background_callback_manager,
                    "call_job_fn",
                    return_value="fixture-job",
                ) as submit,
                patch.object(
                    app, "_get_signing_secret", return_value=b"fixture-secret" * 4
                ),
            ):
                response = app.server.test_client().post(
                    "/staci-app/_dash-update-component",
                    json=body,
                    headers={
                        "X-Staci-User-Id": user_id,
                        "X-Staci-User-Login": "user" + user_id,
                    },
                )
            assert response.status_code == 200
            # JSON serialization models the real broker boundary.
            requests_and_contexts.append(
                (
                    request_state,
                    json.loads(json.dumps(submit.call_args.args[3])),
                )
            )
        celery = Celery(
            "logging-fixture", broker="memory://", backend="cache+memory://"
        )
        manager = CeleryManager(celery)
        task = manager.make_job_fn(
            callback["callback"].__wrapped__, progress=False, key="logging-fixture"
        )
        state = {"run_id": "123456abcdef", "model_id": model["model_id"], "summary": {}}
        with (
            patch.object(
                hydraulic_callbacks,
                "resolve_uploaded_model",
                new=_fake_running_solver_job,
            ),
            patch.object(
                hydraulic_callbacks, "call_hydraulic_simulator", return_value=state
            ),
            patch.object(
                hydraulic_callbacks,
                "render_success_alert",
                return_value="original-alert",
            ),
        ):
            for index, (request_state, context) in enumerate(requests_and_contexts):
                task.run(
                    "result" + str(index),
                    "progress" + str(index),
                    [request_state],
                    context,
                )
                assert json.loads(celery.backend.get("result" + str(index))) == [
                    state,
                    "original-alert",
                ]
        assert execution_id.get() == "-"
        logging.info("outside-task")
        lines = (tmp_path / "application.log").read_text().splitlines()
        events = [
            (line, json.loads(line.split("STACI_RUN ", 1)[1]))
            for line in lines
            if "STACI_RUN " in line
        ]
        starts = [
            (line, event) for line, event in events if event["event"] == "started"
        ]
        assert len(starts) == 2
        assert starts[0][1]["execution_id"] != starts[1][1]["execution_id"]
        for index, user_id in enumerate(("7", "8")):
            run_id = starts[index][1]["execution_id"]
            run_lines = [line for line in lines if "execution_id=" + run_id in line]
            assert run_lines and all(
                f'user_id={user_id} user="user{user_id}"' in line for line in run_lines
            )
            assert any('"event":"finished"' in line for line in run_lines)
        assert "user_id=- user=- | outside-task" in lines[-1]
    finally:
        for handler in logging.root.handlers:
            handler.close()
        logging.root.handlers = old_handlers
        logging.root.setLevel(old_level)


def test_worker_logging_setup_installs_application_handlers():
    with patch("src.logging_setup.configure_logging") as configure:
        setup_worker_logging(loglevel=logging.INFO)
    configure.assert_called_once()


def test_partial_flushing_result_is_logged_as_warning_without_changing_result():
    registry = CallbackRegistry()
    flushing_callbacks.register_flushing_callbacks(registry)
    model = {"model_id": "abcdef123456", "filename": "flush.inp"}
    state = {
        "run_id": "123456abcdef",
        "model_id": model["model_id"],
        "partial": True,
        "status": "partial",
        "scenario_count": 1,
        "plan_count": 1,
    }
    with (
        patch.object(
            flushing_callbacks,
            "resolve_uploaded_model",
            return_value=Path("/test/input.inp"),
        ),
        patch.object(
            flushing_callbacks, "call_staci_flush_service", return_value=state
        ) as runner,
        patch("src.run_logging.event") as event,
    ):
        result = registry.functions["run_flushing"](
            1, model, "A", "single", 0.002, 2, 0.5, 0, False
        )
    assert result[0] is state
    assert runner.call_args.kwargs["hydrant_node_ids"] == ["A"]
    finished = next(
        call.kwargs for call in event.call_args_list if call.args[0] == "finished"
    )
    assert finished["status"] == "completed_with_warnings"
