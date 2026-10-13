"""Verify real Dash-to-Celery context transfer using an isolated in-memory backend."""
import json
import logging
from pathlib import Path
from unittest.mock import patch

from celery import Celery
from dash import CeleryManager

from app import app
from src.background_jobs import background_callback_manager, setup_worker_logging
from src.logging_setup import configure_logging
from src.run_logging import execution_id
from src.ui.callbacks import hydraulic_callbacks, flushing_callbacks
from tests.test_run_callbacks import CallbackRegistry


def test_background_task_preserves_verified_user_and_run_context(tmp_path, monkeypatch):
    old_handlers = logging.root.handlers[:]
    old_level = logging.root.level
    monkeypatch.setenv('STACI_LOG_DIR', str(tmp_path))
    monkeypatch.setenv('STACI_LOG_READER_GID', '')
    configure_logging()
    try:
        # Capture the exact context Dash constructs from the HTTP request.
        key, callback = next((key, value) for key, value in app.callback_map.items()
                             if 'hyd-run-store.data' in key and 'hyd-run-status.children' in key)
        model = {'model_id': 'abcdef123456', 'filename': 'same.inp'}
        values = [1, model, 'wntr', False, 1, 5]
        contexts = []
        for user_id in ('7', '8'):
            body = {
                'output': key,
                'outputs': [{'id': item.component_id, 'property': item.component_property} for item in callback['output']],
                'inputs': [dict(item, value=values[0]) for item in callback['inputs']],
                'state': [dict(item, value=value) for item, value in zip(callback['state'], values[1:])],
                'changedPropIds': ['hyd-run-button.n_clicks'],
            }
            with patch.object(background_callback_manager, 'call_job_fn', return_value='fixture-job') as submit, \
                 patch.object(app, '_get_signing_secret', return_value=b'fixture-secret' * 4):
                response = app.server.test_client().post('/staci-app/_dash-update-component', json=body,
                    headers={'X-Staci-User-Id': user_id, 'X-Staci-User-Login': 'user' + user_id})
            assert response.status_code == 200
            # JSON serialization models the real broker boundary.
            contexts.append(json.loads(json.dumps(submit.call_args.args[3])))
        celery = Celery('logging-fixture', broker='memory://', backend='cache+memory://')
        manager = CeleryManager(celery)
        task = manager.make_job_fn(callback['callback'].__wrapped__, progress=False, key='logging-fixture')
        state = {'run_id': '123456abcdef', 'model_id': model['model_id'], 'summary': {}}
        with patch.object(hydraulic_callbacks, 'resolve_uploaded_model', return_value=Path('/test/input.inp')), \
             patch.object(hydraulic_callbacks, 'call_hydraulic_simulator', return_value=state), \
             patch.object(hydraulic_callbacks, 'render_success_alert', return_value='original-alert'):
            for index, context in enumerate(contexts):
                task.run('result' + str(index), 'progress' + str(index), values, context)
                assert json.loads(celery.backend.get('result' + str(index))) == [state, 'original-alert']
        assert execution_id.get() == '-'
        logging.info('outside-task')
        lines = (tmp_path / 'application.log').read_text().splitlines()
        events = [(line, json.loads(line.split('STACI_RUN ', 1)[1])) for line in lines if 'STACI_RUN ' in line]
        starts = [(line, event) for line, event in events if event['event'] == 'started']
        assert len(starts) == 2
        assert starts[0][1]['execution_id'] != starts[1][1]['execution_id']
        for index, user_id in enumerate(('7', '8')):
            run_id = starts[index][1]['execution_id']
            run_lines = [line for line in lines if 'execution_id=' + run_id in line]
            assert run_lines and all(f'user_id={user_id} user="user{user_id}"' in line for line in run_lines)
            assert any('"event":"finished"' in line for line in run_lines)
        assert 'user_id=- user=- | outside-task' in lines[-1]
    finally:
        for handler in logging.root.handlers:
            handler.close()
        logging.root.handlers = old_handlers
        logging.root.setLevel(old_level)


def test_worker_logging_setup_installs_application_handlers():
    with patch('src.logging_setup.configure_logging') as configure:
        setup_worker_logging(loglevel=logging.INFO)
    configure.assert_called_once()


def test_partial_flushing_result_is_logged_as_warning_without_changing_result():
    registry = CallbackRegistry()
    flushing_callbacks.register_flushing_callbacks(registry)
    model = {'model_id': 'abcdef123456', 'filename': 'flush.inp'}
    state = {'run_id': '123456abcdef', 'model_id': model['model_id'],
             'partial': True, 'status': 'partial', 'scenario_count': 1, 'plan_count': 1}
    with patch.object(flushing_callbacks, 'resolve_uploaded_model', return_value=Path('/test/input.inp')), \
         patch.object(flushing_callbacks, 'call_staci_flush_service', return_value=state) as runner, \
         patch('src.run_logging.event') as event:
        result = registry.functions['run_flushing'](1, model, 'A', 'single', .002, 2, .5, 0, False)
    assert result[0] is state
    assert runner.call_args.kwargs['hydrant_node_ids'] == ['A']
    finished = next(call.kwargs for call in event.call_args_list if call.args[0] == 'finished')
    assert finished['status'] == 'completed_with_warnings'
