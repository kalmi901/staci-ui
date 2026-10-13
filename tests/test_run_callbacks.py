"""Exercise real Dash callbacks with isolated runner doubles, never production data."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.ui.callbacks import hydraulic_callbacks, partitioning_callbacks
from src.run_logging import execution_id


class CallbackRegistry:
    def __init__(self):
        self.functions = {}

    def callback(self, *args, **kwargs):
        def register(function):
            self.functions[function.__name__] = function
            return function
        return register


class RunCallbackTests(unittest.TestCase):
    def test_real_callbacks_preserve_results_parameters_and_handled_errors(self):
        registry = CallbackRegistry()
        hydraulic_callbacks.register_hydraulic_callbacks(registry)
        partitioning_callbacks.register_partitioning_callbacks(registry)
        model = {'model_id': 'abcdef123456', 'filename': 'network.inp'}
        state = {'run_id': '123456abcdef', 'model_id': model['model_id'], 'backend': 'wntr', 'summary': {}}
        with patch.object(hydraulic_callbacks, 'resolve_uploaded_model', return_value=Path('/test/network.inp')), \
             patch.object(hydraulic_callbacks, 'call_hydraulic_simulator', return_value=state) as runner, \
             patch.object(hydraulic_callbacks, 'render_success_alert', return_value='original-success'):
            result = registry.functions['run_hydraulic_simulation'](1, model, 'wntr', True, 2, 5)
            self.assertEqual(result, (state, 'original-success'))
            self.assertEqual(runner.call_args.kwargs['option_overrides'], {'duration': 7200, 'hydraulic_timestep': 300})
            with self.assertLogs('src.run_logging', level='INFO') as logs:
                failed = registry.functions['run_hydraulic_simulation'](1, model, 'wntr', True, None, 5)
            self.assertIsNone(failed[0])
            self.assertTrue(any('"status":"failed"' in line for line in logs.output))
        with patch.object(partitioning_callbacks, 'resolve_uploaded_model', return_value=Path('/test/network.inp')), \
             patch.object(partitioning_callbacks, 'call_staci_split_service', return_value=state) as runner, \
             patch.object(partitioning_callbacks, 'render_success_alert', return_value='original-success'):
            result = registry.functions['run_partitioning'](1, model, 3, 'modularity', 'topology', 'diameter', 20, 50, .25, .8, 42)
            self.assertEqual(result, (state, 'original-success'))
            self.assertEqual(runner.call_args.kwargs['seed'], 42)
            self.assertEqual(runner.call_args.kwargs['optimizer_settings']['popsize'], 20)
        self.assertEqual(execution_id.get(), '-')

    def test_dash_http_callback_still_accepts_original_payload(self):
        from app import app
        from src.background_jobs import background_callback_manager
        key, callback = next((key, value) for key, value in app.callback_map.items()
                             if 'hyd-run-store.data' in key and 'hyd-run-status.children' in key)
        values = [None, 'wntr', False, 1, 5]
        body = {
            'output': key,
            'outputs': [{'id': item.component_id, 'property': item.component_property} for item in callback['output']],
            'inputs': [dict(item, value=1) for item in callback['inputs']],
            'state': [dict(item, value=value) for item, value in zip(callback['state'], values)],
            'changedPropIds': ['hyd-run-button.n_clicks'],
        }
        with patch.object(background_callback_manager, 'call_job_fn', return_value='fixture-job') as submit, \
             patch.object(app, '_get_signing_secret', return_value=b'fixture-secret' * 4):
            response = app.server.test_client().post('/staci-app/_dash-update-component', json=body,
                headers={'X-Staci-User-Id': '7', 'X-Staci-User-Login': 'worker-test'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('job', response.get_json())
        self.assertEqual(submit.call_args.args[2], [1, *values])
        self.assertEqual(submit.call_args.args[3]['headers']['X-Staci-User-Id'], '7')

    def test_hydraulic_runner_records_effective_copied_input_before_solver(self):
        from src.services import hydraulic_runner
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'original.inp'
            original.write_text('original')
            def override(source, options, destination):
                destination.write_text('effective')
            with patch.object(hydraulic_runner, 'RUN_ROOT', root / 'runs'), \
                 patch.object(hydraulic_runner, 'set_model_options', side_effect=override), \
                 patch.object(hydraulic_runner, 'read_model_options', return_value={'duration': 7200}), \
                 patch.object(hydraulic_runner, 'run_wntr', return_value={'same': 'result'}) as solver:
                token = execution_id.set('f' * 32)
                try:
                    with self.assertLogs('src.run_logging', level='INFO') as logs:
                        result = hydraulic_runner.call_hydraulic_simulator(original, model_id='abcdef123456', backend='wntr', option_overrides={'duration': 7200})
                finally:
                    execution_id.reset(token)
            self.assertEqual(result, {'same': 'result'})
            self.assertEqual(Path(solver.call_args.args[0]).read_text(), 'effective')
            self.assertEqual(original.read_text(), 'original')
            events = [json.loads(line.split('STACI_RUN ', 1)[1]) for line in logs.output if 'STACI_RUN ' in line]
            prepared = next(e for e in events if e['event'] == 'prepared')
            self.assertEqual(prepared['effective_options']['duration'], 7200)
            self.assertEqual(prepared['run_id'], solver.call_args.args[2])

if __name__ == '__main__':
    unittest.main()
