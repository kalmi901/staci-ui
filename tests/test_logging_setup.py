import concurrent.futures
import logging
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask

from src.logging_setup import configure_logging


class LoggingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.app = Flask(__name__)
        self.original_handlers = logging.root.handlers[:]
        self.original_level = logging.root.level
        logging.root.handlers = []
        with patch.dict(os.environ, {"STACI_LOG_DIR": self.temp.name}, clear=True):
            configure_logging()

    def tearDown(self):
        for handler in logging.root.handlers:
            handler.close()
        logging.root.handlers = self.original_handlers
        logging.root.setLevel(self.original_level)
        self.temp.cleanup()

    def contents(self):
        return (self.directory / "application.log").read_text()

    def test_user_context_does_not_leak_between_requests_or_threads(self):
        def emit(user_id):
            with self.app.test_request_context(headers={
                "X-Staci-User-Id": str(user_id),
                "X-Staci-User-Login": f"person{user_id}",
            }):
                logging.getLogger("workflow").info("event-%d", user_id)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(emit, range(1, 21)))
        for line in self.contents().splitlines():
            user_id = line.rsplit("event-", 1)[1]
            self.assertIn(f'user_id={user_id} user="person{user_id}"', line)
        logging.info("outside-request")
        self.assertIn("user_id=- user=- | outside-request", self.contents())

    def test_missing_or_invalid_identity_and_control_characters(self):
        with self.app.test_request_context(headers={"X-Staci-User-Id": "abc"}):
            logging.info("invalid-identity")
        with self.app.test_request_context(headers={
            "X-Staci-User-Id": "42", "X-Staci-User-Login": "ann%0Aforged%22",
        }):
            logging.info("escaped-identity")
        lines = self.contents().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("user_id=- user=-", lines[0])
        self.assertIn('user="ann\\nforged\\\""', lines[1])

    def test_exception_is_preserved_and_file_permissions_survive_rotation(self):
        handler = logging.root.handlers[1]
        handler.maxBytes = 700
        handler.backupCount = 2
        for index in range(100):
            logging.info("rotation-%d %s", index, "x" * 60)
        with self.app.test_request_context(headers={
            "X-Staci-User-Id": "7", "X-Staci-User-Login": "tester",
        }):
            try:
                raise ValueError("expected-test-error")
            except ValueError:
                logging.exception("workflow failed")
        files = sorted(self.directory.glob("application.log*"))
        self.assertEqual(len(files), 3)
        for file in files:
            self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o640)
        self.assertIn('user_id=7 user="tester"', self.contents())
        self.assertIn("ValueError: expected-test-error", self.contents())


if __name__ == "__main__":
    unittest.main()
