from __future__ import annotations

from celery import Celery
from celery.signals import setup_logging
from dash import CeleryManager
from redis import Redis

from src.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_RESULT_EXPIRES_SECONDS,
    CELERY_WORKER_CONCURRENCY,
    DASH_DEBUG,
)
from src.services.solver_jobs import SolverJobRegistry

celery_app = Celery(
    "staci_ui",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)


redis_client = Redis.from_url(CELERY_BROKER_URL, decode_responses=True)

solver_job_registry = SolverJobRegistry(
    redis_client,
    ttl_seconds=CELERY_RESULT_EXPIRES_SECONDS,
    capacity=CELERY_WORKER_CONCURRENCY,
)


celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    result_expires=CELERY_RESULT_EXPIRES_SECONDS,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


@setup_logging.connect
def setup_worker_logging(**kwargs):
    # Celery's default logging setup would replace our user-aware handlers.
    from src.logging_setup import configure_logging

    configure_logging(debug=DASH_DEBUG)


background_callback_manager = CeleryManager(celery_app)
