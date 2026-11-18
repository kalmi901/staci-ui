from __future__ import annotations

import re
from pathlib import Path

_STRUCTURED_ERROR = re.compile(
    (
        r"^ERROR\s+"
        r"(?:\[[^\]]+\])+"
        r"\s*:\s*"
        r"(?P<message>.+)$"
    ),
    re.IGNORECASE,
)

_RAW_ERROR = re.compile(
    (
        r"^(?:!+\s*)?"
        r"ERROR"
        r"(?:\s*!+)?"
        r"\s*:?\s*"
        r"(?P<message>.+)$"
    ),
    re.IGNORECASE,
)

_CONTEXT_WRAPPER = re.compile(
    r"(?:^|:\s*)Application stopped\. Context:\s*$",
    re.IGNORECASE,
)

_MAX_DETAILS = 3
_MAX_DETAIL_LENGTH = 400


def _read_lines(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return []


def _add_unique(
    details: list[str],
    detail: str,
) -> None:
    detail = detail.strip()

    if not detail:
        return

    if len(detail) > _MAX_DETAIL_LENGTH:
        detail = detail[: _MAX_DETAIL_LENGTH - 3] + "..."

    if detail not in details:
        details.append(detail)


def _extract_error_details(
    path: Path | None,
) -> list[str]:
    structured: list[str] = []
    legacy: list[str] = []

    for raw_line in _read_lines(path):
        line = raw_line.strip()

        if not line:
            continue

        structured_match = _STRUCTURED_ERROR.match(line)

        if structured_match:
            detail = structured_match.group("message")

            # The executable may emit a second generic wrapper
            # after the actual error. It adds no useful information.
            if not _CONTEXT_WRAPPER.search(detail):
                _add_unique(structured, detail)

            continue

        legacy_match = _RAW_ERROR.match(line)

        if legacy_match:
            _add_unique(
                legacy,
                legacy_match.group("message"),
            )

    # New STACI builds emit structured ERROR lines and may repeat
    # the same message in the legacy output below them.
    return structured or legacy


def format_staci_failure(
    tool_name: str,
    returncode: int | None,
    *,
    stderr_path: Path,
    stdout_path: Path | None = None,
) -> str:
    details = _extract_error_details(stderr_path)

    # Older Split builds occasionally write fatal errors to stdout.
    if not details:
        details = _extract_error_details(stdout_path)

    message = f"{tool_name} failed (return code {returncode})."

    if not details:
        return message

    visible_details = details[:_MAX_DETAILS]
    message += " " + "; ".join(visible_details)

    hidden_count = len(details) - len(visible_details)

    if hidden_count:
        noun = "error" if hidden_count == 1 else "errors"
        message += f" (+{hidden_count} more {noun}.)"

    return message
