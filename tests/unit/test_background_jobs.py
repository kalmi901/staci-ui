from dash import CeleryManager

from src.background_jobs import (
    background_callback_manager,
    celery_app,
)
from src.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_RESULT_EXPIRES_SECONDS,
)


def test_background_manager_uses_configured_celery_app() -> None:
    assert isinstance(
        background_callback_manager,
        CeleryManager,
    )

    assert celery_app.main == "staci_ui"
    assert celery_app.conf.broker_url == CELERY_BROKER_URL
    assert (
        celery_app.conf.result_backend
        == CELERY_RESULT_BACKEND
    )
    assert (
        celery_app.conf.result_expires
        == CELERY_RESULT_EXPIRES_SECONDS
    )
    assert celery_app.conf.task_track_started is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert (
        celery_app.conf.broker_connection_retry_on_startup
        is True
    )