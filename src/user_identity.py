"""Access the proxy-verified WordPress user identity.

Production requests may reach the application only through Caddy.
Caddy removes externally supplied identity headers and replaces them
with values returned by the authenticated WordPress endpoint.

Dash transfers these request headers into the callback context when a
background callback is executed by Celery.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import unquote

from dash import ctx
from dash.exceptions import (
    MissingCallbackContextException,
)
from flask import has_request_context, request

_USER_ID_PATTERN = re.compile(r"[1-9][0-9]{0,19}")


@dataclass(frozen=True)
class UserIdentity:
    user_id: str
    login: str


def identity_from_headers(
    headers: Mapping[str, str] | None,
) -> UserIdentity | None:
    if not headers:
        return None

    user_id = headers.get(
        "X-Staci-User-Id",
        "",
    )
    encoded_login = headers.get(
        "X-Staci-User-Login",
        "",
    )

    if not _USER_ID_PATTERN.fullmatch(user_id) or not encoded_login:
        return None

    login = unquote(encoded_login[:512])[:128]

    return UserIdentity(
        user_id=user_id,
        login=login,
    )


def development_user_identity() -> UserIdentity | None:
    """Return the explicitly configured local-development identity."""

    user_id = os.getenv("STACI_UI_DEV_USER_ID", "")
    login = os.getenv("STACI_UI_DEV_USER_LOGIN", "")

    if not _USER_ID_PATTERN.fullmatch(user_id) or not login:
        return None

    return UserIdentity(
        user_id=user_id,
        login=login[:128],
    )


def current_user_identity() -> UserIdentity | None:
    identity = None

    if has_request_context():
        identity = identity_from_headers(
            request.headers  # pyright: ignore[reportArgumentType]
        )

    else:
        try:
            identity = identity_from_headers(ctx.headers)
        except (
            MissingCallbackContextException,
            LookupError,
        ):
            pass

    if identity is not None:
        return identity

    return development_user_identity()
