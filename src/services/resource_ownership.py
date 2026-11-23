from __future__ import annotations

import json
import re
from pathlib import Path

_OWNER_FILENAME = ".owner.json"
_USER_ID_PATTERN = re.compile(r"[1-9][0-9]{0,19}")
_ACCESS_DENIED_MESSAGE = "Resource is not available for the current user."


def _validated_user_id(user_id: str) -> str:
    if not isinstance(user_id, str) or not _USER_ID_PATTERN.fullmatch(user_id):
        raise ValueError("A valid verified user ID is required.")

    return user_id


def _owner_path(resource_dir: Path) -> Path:
    return Path(resource_dir) / _OWNER_FILENAME


def write_resource_owner(
    resource_dir: Path,
    user_id: str,
) -> None:
    resource_dir = Path(resource_dir)
    validated_user_id = _validated_user_id(user_id)

    if not resource_dir.is_dir():
        raise FileNotFoundError(f"Resource directory does not exist: {resource_dir}")

    owner_path = _owner_path(resource_dir)

    try:
        with owner_path.open(
            "x",
            encoding="utf-8",
            newline="\n",
        ) as owner_file:
            json.dump(
                {
                    "schema": 1,
                    "user_id": validated_user_id,
                },
                owner_file,
                separators=(",", ":"),
                sort_keys=True,
            )
            owner_file.write("\n")

    except FileExistsError:
        require_resource_owner(
            resource_dir,
            validated_user_id,
        )


def require_resource_owner(
    resource_dir: Path,
    user_id: str,
) -> None:
    resource_dir = Path(resource_dir)
    validated_user_id = _validated_user_id(user_id)
    owner_path = _owner_path(resource_dir)

    try:
        metadata = json.loads(owner_path.read_text(encoding="utf-8"))
    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ):
        raise PermissionError(_ACCESS_DENIED_MESSAGE) from None

    if (
        not isinstance(metadata, dict)
        or metadata.get("schema") != 1
        or metadata.get("user_id") != validated_user_id
    ):
        raise PermissionError(_ACCESS_DENIED_MESSAGE)
