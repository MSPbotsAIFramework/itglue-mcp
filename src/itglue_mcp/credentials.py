# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Per-request credentials, taken only from request headers.

The gateway sends each tenant's credentials on every request. They live in a
ContextVar for the duration of that request and are never stored anywhere else.
"""

import contextvars
from dataclasses import dataclass
from urllib.parse import urlparse

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import (
    ALLOWED_BASE_URL_SUFFIX,
    API_KEY_HEADER,
    BASE_URL_HEADER,
    DEFAULT_REGION,
    REGION_BASE_URLS,
    REGION_HEADER,
)


@dataclass(frozen=True)
class Credentials:
    api_key: str
    base_url: str


_current: contextvars.ContextVar[Credentials | None] = contextvars.ContextVar("itglue_credentials", default=None)


def current() -> Credentials | None:
    return _current.get()


class CredentialError(ValueError):
    pass


def resolve_base_url(region: str | None, base_url: str | None) -> str:
    """A custom base URL wins over the region; both are validated."""
    if base_url and base_url.strip():
        url = base_url.strip().rstrip("/")
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (
            host == ALLOWED_BASE_URL_SUFFIX.lstrip(".") or host.endswith(ALLOWED_BASE_URL_SUFFIX)
        ):
            raise CredentialError(
                f"{BASE_URL_HEADER} must be an https URL on an IT Glue host (*{ALLOWED_BASE_URL_SUFFIX})."
            )
        return f"{parsed.scheme}://{parsed.netloc}"

    key = (region or DEFAULT_REGION).strip().lower() or DEFAULT_REGION
    if key not in REGION_BASE_URLS:
        raise CredentialError(f"{REGION_HEADER} must be one of: {', '.join(REGION_BASE_URLS)}.")
    return REGION_BASE_URLS[key]


def _reject(status: int, message: str) -> JSONResponse:
    return JSONResponse(
        {
            "error": "Missing or invalid credentials" if status == 401 else "Invalid credentials",
            "message": message,
            "required_headers": [API_KEY_HEADER],
            "optional_headers": [REGION_HEADER, BASE_URL_HEADER],
        },
        status_code=status,
    )


class CredentialMiddleware:
    """Reads the IT Glue headers on /mcp requests and binds them to the request context."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        api_key = (request.headers.get(API_KEY_HEADER) or "").strip()
        if not api_key:
            await _reject(401, f"Send your IT Glue API key in the {API_KEY_HEADER} header.")(scope, receive, send)
            return
        try:
            base_url = resolve_base_url(request.headers.get(REGION_HEADER), request.headers.get(BASE_URL_HEADER))
        except CredentialError as exc:
            await _reject(400, str(exc))(scope, receive, send)
            return

        token = _current.set(Credentials(api_key=api_key, base_url=base_url))
        try:
            await self.app(scope, receive, send)
        finally:
            _current.reset(token)
