from __future__ import annotations

from celery import Celery
from dash import CeleryManager

from src.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_RESULT_EXPIRES_SECONDS,
)


celery_app = Celery(
    "staci_ui",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    result_expires=CELERY_RESULT_EXPIRES_SECONDS,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

background_callback_manager = CeleryManager(celery_app)