import concurrent.futures
import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.run_logging import execution_id, logged_run, log_prepared_input
from src.logging_setup import RequestUserFilter


class RunLoggingTests(unittest.TestCase):
    def setUp(self):
        self.records = []
        self.logger = logging.getLogger('src.run_logging')
        self.old_level = self.logger.level
        self.logger.setLevel(logging.INFO)
        class Capture(logging.Handler):
            def emit(inner, record):
                RequestUserFilter().filter(record)
                self.records.append(record)
        self.handler = Capture()
        self.logger.addHandler(self.handler)
        self.version = patch('src.run_logging.application_version', return_value={'source_sha256': 'fixture'})
        self.version.start()

    def tearDown(self):
        self.version.stop()
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.old_level)

    def events(self):
        return [json.loads(record.getMessage()[10:]) for record in self.records
                if record.getMessage().startswith('STACI_RUN ')]

    def test_concurrent_callbacks_keep_distinct_ids_and_unchanged_return_values(self):
        @logged_run('hydraulic')
        def callback(n_clicks, network_state, backend):
            return {'run_id': str(network_state['model_id']), 'summary': {'failed_frames': 0}}, 'unchanged'
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda i: callback(1, {'model_id': str(i), 'filename': f'{i}.inp'}, 'wntr'), range(20)))
        self.assertEqual([item[0]['run_id'] for item in results], [str(i) for i in range(20)])
        starts = {event['execution_id']: event for event in self.events() if event['event'] == 'started'}
        ends = [event for event in self.events() if event['event'] == 'finished']
        self.assertEqual(len(starts), 20)
        for event in ends:
            self.assertEqual(event['run_id'], starts[event['execution_id']]['model_id'])
        self.assertEqual(execution_id.get(), '-')
        self.assertTrue(all(record.staci_execution_id != '-' for record in self.records))

    def test_handled_failure_warning_exception_and_no_click(self):
        @logged_run('hydraulic')
        def callback(n_clicks, network_state, backend):
            if backend == 'raise':
                raise ValueError('expected')
            if backend == 'failed':
                return None, 'original alert'
            return {'run_id': '123', 'summary': {'failed_frames': 97}}, 'original result'
        self.assertEqual(callback(1, {'model_id': 'abc'}, 'failed'), (None, 'original alert'))
        callback(1, {'model_id': 'abc'}, 'warning')
        with self.assertRaisesRegex(ValueError, 'expected'):
            callback(1, {'model_id': 'abc'}, 'raise')
        self.assertEqual(execution_id.get(), '-')
        ends = [event['status'] for event in self.events() if event['event'] == 'finished']
        self.assertEqual(ends, ['failed', 'completed_with_warnings', 'failed'])
        count = len(self.events())
        callback(0, {'model_id': 'abc'}, 'warning')
        self.assertEqual(len(self.events()), count)

    def test_hash_actual_input_and_inspection_failure_does_not_raise(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.inp'
            path.write_bytes(b'abc')
            token = execution_id.set('a' * 32)
            try:
                log_prepared_input(path, 'run1', options_reader=lambda p: {'duration': 60})
                log_prepared_input(path, 'run2', options_reader=lambda p: 1 / 0)
            finally:
                execution_id.reset(token)
            event = next(e for e in self.events() if e['event'] == 'prepared')
            self.assertEqual(event['input_sha256'], 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
            self.assertEqual(event['effective_options']['duration'], 60)
            self.assertEqual(path.read_bytes(), b'abc')
            self.assertTrue(any(e['run_id'] == 'run2' for e in self.events() if e['event'] == 'allocated'))

if __name__ == '__main__':
    unittest.main()
