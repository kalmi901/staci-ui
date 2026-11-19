from __future__ import annotations

import pytest
from dash._callback_context import context_value
from dash._utils import AttributeDict
from flask import Flask

from src.user_identity import (
    UserIdentity,
    current_user_identity,
    identity_from_headers,
)


def test_identity_from_headers_returns_user() -> None:
    identity = identity_from_headers(
        {
            "X-Staci-User-Id": "42",
            "X-Staci-User-Login": ("worker%20user"),
        }
    )

    assert identity == UserIdentity(
        user_id="42",
        login="worker user",
    )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {
            "X-Staci-User-Id": "42",
        },
        {
            "X-Staci-User-Login": "user",
        },
        {
            "X-Staci-User-Id": "0",
            "X-Staci-User-Login": "user",
        },
        {
            "X-Staci-User-Id": "-1",
            "X-Staci-User-Login": "user",
        },
        {
            "X-Staci-User-Id": "abc",
            "X-Staci-User-Login": "user",
        },
        {
            "X-Staci-User-Id": "1" * 21,
            "X-Staci-User-Login": "user",
        },
    ],
)
def test_identity_from_headers_rejects_invalid_identity(
    headers: dict[str, str],
) -> None:
    assert identity_from_headers(headers) is None


def test_identity_login_is_decoded_and_bounded() -> None:
    identity = identity_from_headers(
        {
            "X-Staci-User-Id": "7",
            "X-Staci-User-Login": ("name%20" + "x" * 200),
        }
    )

    assert identity is not None
    assert identity.login.startswith("name ")
    assert len(identity.login) == 128


def test_current_user_identity_uses_flask_request() -> None:
    app = Flask(__name__)

    with app.test_request_context(
        headers={
            "X-Staci-User-Id": "41",
            "X-Staci-User-Login": "alice",
        }
    ):
        identity = current_user_identity()

    assert identity == UserIdentity(
        user_id="41",
        login="alice",
    )


def test_current_user_identity_uses_dash_context() -> None:
    token = context_value.set(
        AttributeDict(
            headers={
                "X-Staci-User-Id": "42",
                "X-Staci-User-Login": ("background%20user"),
            }
        )
    )

    try:
        identity = current_user_identity()
    finally:
        context_value.reset(token)

    assert identity == UserIdentity(
        user_id="42",
        login="background user",
    )


def test_current_user_identity_is_none_outside_context() -> None:
    assert current_user_identity() is None


def test_current_user_identity_uses_explicit_development_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "STACI_UI_DEV_USER_ID",
        "99",
    )
    monkeypatch.setenv(
        "STACI_UI_DEV_USER_LOGIN",
        "local-developer",
    )

    assert current_user_identity() == UserIdentity(
        user_id="99",
        login="local-developer",
    )


def test_verified_identity_takes_precedence_over_development_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "STACI_UI_DEV_USER_ID",
        "99",
    )
    monkeypatch.setenv(
        "STACI_UI_DEV_USER_LOGIN",
        "local-developer",
    )

    app = Flask(__name__)

    with app.test_request_context(
        headers={
            "X-Staci-User-Id": "41",
            "X-Staci-User-Login": "verified-user",
        }
    ):
        identity = current_user_identity()

    assert identity == UserIdentity(
        user_id="41",
        login="verified-user",
    )
