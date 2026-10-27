# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Shared plumbing for tool handlers."""

import logging
from collections.abc import Awaitable, Callable, Iterable
from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import Field

from .. import _json
from ..api import ApiError, ITGlueClient
from ..config import API_KEY_HEADER, Settings
from ..credentials import current

log = logging.getLogger("itglue_mcp")

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
CREATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
UPDATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True)
DESTRUCTIVE_IDEMPOTENT = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True
)

PageSize = Annotated[
    int | None,
    Field(description=f"Results per page (default {DEFAULT_PAGE_SIZE}, max {MAX_PAGE_SIZE}).", ge=1),
]
PageNumber = Annotated[int | None, Field(description="Page number, starting at 1 (default 1).", ge=1)]
Offset = Annotated[
    int | None,
    Field(
        description="Record position to start from (0-based; overrides page_number). "
        "Pass next_offset from the previous result.",
        ge=0,
    ),
]


def paging(page_size: int | None, page_number: int | None) -> tuple[int, int, dict[str, int]]:
    size = min(max(page_size or DEFAULT_PAGE_SIZE, 1), MAX_PAGE_SIZE)
    number = max(page_number or 1, 1)
    return size, number, {"page[size]": size, "page[number]": number}


def locate(
    page_size: int | None, page_number: int | None, offset: int | None, fixed_size: int | None = None
) -> tuple[int, int, dict[str, int], int]:
    """(page size, page number, query params, start). The page holding ``offset`` is fetched;
    ``api.page`` then skips the records before it, so a cut page continues exactly."""
    size = fixed_size or min(max(page_size or DEFAULT_PAGE_SIZE, 1), MAX_PAGE_SIZE)
    start = offset if offset is not None else (max(page_number or 1, 1) - 1) * size
    number = start // size + 1
    return size, number, {"page[size]": size, "page[number]": number}, start


Handler = Callable[[ITGlueClient], Awaitable[Any]]


REDACTED = "[redacted]"

# Marks a tool parameter as a secret in the input schema (standard JSON Schema hints), so callers
# and run records can mask it. The value is never logged or echoed by this server.
SECRET_SCHEMA = {"format": "password", "writeOnly": True}


def redact(text: str, secrets: Iterable[str | None]) -> str:
    """Replace every occurrence of the given secret values in ``text``."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    return text


async def run(settings: Settings, handler: Handler, secrets: Iterable[str | None] = ()) -> str:
    """Execute ``handler`` with a client bound to this request's credentials.

    Always returns a string: the JSON result, or an error envelope. ``secrets`` (e.g. a password
    the caller passed) are masked in error messages and never written to the log.
    """
    secrets = [s for s in secrets if s]
    creds = current()
    if creds is None:
        return _json.error("not_configured", f"No IT Glue credentials. Send the {API_KEY_HEADER} header.")
    if creds.header_error:
        return _json.error("invalid_argument", creds.header_error)
    try:
        async with ITGlueClient(creds, settings) as client:
            result = await handler(client)
    except ApiError as exc:
        return _json.error(exc.code, redact(exc.message, secrets), exc.retryable)
    except ToolInputError as exc:
        return _json.error("invalid_argument", redact(str(exc), secrets))
    except Exception as exc:  # noqa: BLE001 - tools must never raise
        if secrets:
            # No traceback: its frames and messages could carry the secret.
            log.error("unexpected error in tool handler: %s", type(exc).__name__)
        else:
            log.exception("unexpected error in tool handler")
        return _json.error("upstream_error", "Unexpected error while calling IT Glue.", True)
    return result if isinstance(result, str) else _json.dump(result)


class ToolInputError(ValueError):
    """Raised by handlers for arguments IT Glue would reject anyway."""


def seg(value: object) -> str:
    """Path segment for an ID. Only plain numbers are accepted, so IDs cannot alter the URL path."""
    text = str(value).strip()
    if not text.isdigit():
        raise ToolInputError(f"Expected a numeric ID, got {text!r}.")
    return text
