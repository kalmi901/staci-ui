"""Existing application logs, enriched with the proxy-verified WordPress user.

File rotation assumes the deployment's single Gunicorn process (four threads).
Only Caddy may reach the app; it must replace both identity headers after auth.
"""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import time
from urllib.parse import unquote

from flask import has_request_context, request


class RequestUserFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.staci_user_id = "-"
        record.staci_user_login = "-"
        if has_request_context():
            user_id = request.headers.get("X-Staci-User-Id", "")
            login = request.headers.get("X-Staci-User-Login", "")
            if re.fullmatch(r"[1-9][0-9]{0,19}", user_id) and login:
                record.staci_user_id = user_id
                # JSON quoting keeps control characters from forging log lines.
                record.staci_user_login = json.dumps(
                    unquote(login[:512])[:128], ensure_ascii=True
                )
        return True


class PrivateRotatingFileHandler(RotatingFileHandler):
    def _open(self):
        descriptor = os.open(
            self.baseFilename, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640
        )
        return os.fdopen(descriptor, self.mode, encoding=self.encoding, errors=self.errors)


def configure_logging(*, debug: bool = False) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_dir_setting = os.getenv("STACI_LOG_DIR")
    if log_dir_setting:
        log_dir = Path(log_dir_setting)
        log_dir.mkdir(parents=True, exist_ok=True)
        reader_gid = os.getenv("STACI_LOG_READER_GID")
        if reader_gid:
            # Setgid makes new/rotated files readable by WordPress's www-data group.
            os.chown(log_dir, -1, int(reader_gid))
            os.chmod(log_dir, 0o2750)
        handlers.append(PrivateRotatingFileHandler(
            log_dir / "application.log", maxBytes=5 * 1024 * 1024,
            backupCount=5, encoding="utf-8", errors="backslashreplace",
        ))

    formatter = logging.Formatter(
        "%(asctime)sZ | %(levelname)-8s | %(name)s | "
        "user_id=%(staci_user_id)s user=%(staci_user_login)s | %(message)s"
    )
    formatter.converter = time.gmtime
    for handler in handlers:
        handler.addFilter(RequestUserFilter())
        handler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO, handlers=handlers, force=True
    )
