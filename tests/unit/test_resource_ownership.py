from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.services.resource_ownership import (
    require_resource_owner,
    write_resource_owner,
)


def test_write_resource_owner_creates_metadata(
    tmp_path: Path,
) -> None:
    write_resource_owner(tmp_path, "41")

    metadata = json.loads((tmp_path / ".owner.json").read_text(encoding="utf-8"))

    assert metadata == {
        "schema": 1,
        "user_id": "41",
    }

    require_resource_owner(tmp_path, "41")


def test_write_resource_owner_is_idempotent_for_owner(
    tmp_path: Path,
) -> None:
    write_resource_owner(tmp_path, "41")
    write_resource_owner(tmp_path, "41")

    require_resource_owner(tmp_path, "41")


def test_resource_cannot_be_accessed_by_another_user(
    tmp_path: Path,
) -> None:
    write_resource_owner(tmp_path, "41")

    with pytest.raises(
        PermissionError,
        match="not available for the current user",
    ):
        require_resource_owner(tmp_path, "42")

    with pytest.raises(
        PermissionError,
        match="not available for the current user",
    ):
        write_resource_owner(tmp_path, "42")


@pytest.mark.parametrize(
    "owner_contents",
    [
        None,
        "",
        "not-json",
        "{}",
        '{"schema":1}',
        '{"schema":2,"user_id":"41"}',
    ],
)
def test_missing_or_invalid_owner_metadata_is_rejected(
    tmp_path: Path,
    owner_contents: str | None,
) -> None:
    if owner_contents is not None:
        (tmp_path / ".owner.json").write_text(
            owner_contents,
            encoding="utf-8",
        )

    with pytest.raises(
        PermissionError,
        match="not available for the current user",
    ):
        require_resource_owner(tmp_path, "41")


@pytest.mark.parametrize(
    "user_id",
    [
        "",
        "0",
        "-1",
        "user-41",
        "123456789012345678901",
    ],
)
def test_invalid_user_id_is_rejected(
    tmp_path: Path,
    user_id: str,
) -> None:
    with pytest.raises(
        ValueError,
        match="valid verified user ID",
    ):
        write_resource_owner(tmp_path, user_id)
