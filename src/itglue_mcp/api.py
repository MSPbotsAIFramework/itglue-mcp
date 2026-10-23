# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Thin async client for the IT Glue REST API (JSON:API).

Reference: IT Glue developer documentation (https://api.itglue.com/developer/).
- Auth header ``x-api-key``; ``Content-Type: application/vnd.api+json`` on requests with a body.
- Paging via ``page[size]`` / ``page[number]``; filters via ``filter[...]``; sorting via ``sort``.
- Rate limit: 3000 requests per 5 minutes, 429 when exceeded.
"""

import asyncio
import email.utils
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings
from .credentials import Credentials

JSONAPI = "application/vnd.api+json"
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_BACKOFF = 20.0


@dataclass
class ApiError(Exception):
    code: str
    message: str
    retryable: bool = False
    status: int | None = None

    def __str__(self) -> str:
        return self.message


def _status_to_error(status: int, detail: str) -> ApiError:
    if status in (401, 403):
        return ApiError(
            "unauthorized",
            f"IT Glue rejected the API key ({status}). Check the key and its permissions. {detail}".strip(),
            False,
            status,
        )
    if status == 404:
        return ApiError("not_found", f"Not found in IT Glue. {detail}".strip(), False, status)
    if status in (400, 405, 409, 415, 422):
        return ApiError("invalid_argument", f"IT Glue refused the request ({status}). {detail}".strip(), False, status)
    if status == 423:
        return ApiError(
            "invalid_argument", f"Record is locked by an integration sync (423). {detail}".strip(), False, status
        )
    if status == 429:
        return ApiError("rate_limited", "IT Glue rate limit reached. Try again shortly.", True, status)
    return ApiError("upstream_error", f"IT Glue returned {status}. {detail}".strip(), status >= 500, status)


def _error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return ""
    errors = body.get("errors") if isinstance(body, dict) else None
    if not isinstance(errors, list):
        return ""
    parts = []
    for err in errors[:3]:
        if isinstance(err, dict):
            text = err.get("detail") or err.get("title")
            if text:
                parts.append(str(text))
    return "; ".join(parts)[:500]


def _retry_after(response: httpx.Response, attempt: int) -> float:
    value = response.headers.get("retry-after")
    if value:
        try:
            return min(float(value), MAX_BACKOFF)
        except ValueError:
            parsed = email.utils.parsedate_to_datetime(value)
            if parsed is not None:
                return max(0.0, min(parsed.timestamp() - time.time(), MAX_BACKOFF))
    return min(2.0**attempt, MAX_BACKOFF)


class ITGlueClient:
    """One instance per tool call; wraps a single httpx client for that call."""

    def __init__(self, creds: Credentials, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._settings = settings
        self._http = httpx.AsyncClient(
            base_url=creds.base_url,
            headers={"x-api-key": creds.api_key, "Accept": JSONAPI, "User-Agent": "mspbots-itglue-mcp/1.0"},
            timeout=httpx.Timeout(settings.read_timeout, connect=settings.connect_timeout),
            transport=transport,
        )

    async def __aenter__(self) -> "ITGlueClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._http.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any = None,
    ) -> dict[str, Any] | None:
        deadline = time.monotonic() + self._settings.call_budget_seconds
        headers = {"Content-Type": JSONAPI} if body is not None else None
        clean = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        attempt = 0
        while True:
            try:
                response = await self._http.request(method, path, params=clean, json=body, headers=headers)
            except httpx.TimeoutException as exc:
                if attempt < self._settings.max_retries and time.monotonic() + 1 < deadline:
                    attempt += 1
                    await asyncio.sleep(min(2.0**attempt, MAX_BACKOFF))
                    continue
                raise ApiError("upstream_error", "IT Glue did not respond in time.", True) from exc
            except httpx.HTTPError as exc:
                raise ApiError("upstream_error", f"Could not reach IT Glue: {type(exc).__name__}.", True) from exc

            if response.status_code in RETRY_STATUSES and attempt < self._settings.max_retries:
                wait = _retry_after(response, attempt + 1)
                if time.monotonic() + wait < deadline:
                    attempt += 1
                    await asyncio.sleep(wait)
                    continue

            if response.status_code >= 400:
                raise _status_to_error(response.status_code, _error_detail(response))
            if response.status_code == 204 or not response.content:
                return None
            try:
                return response.json()
            except ValueError as exc:
                raise ApiError("upstream_error", "IT Glue returned a response that is not JSON.", True) from exc

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, body: Any, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return await self.request("POST", path, body=body, params=params)

    async def patch(self, path: str, body: Any = None, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return await self.request("PATCH", path, body=body, params=params)

    async def delete(self, path: str, body: Any = None) -> dict[str, Any] | None:
        return await self.request("DELETE", path, body=body)


# ---- JSON:API helpers -------------------------------------------------------


def flatten(resource: dict[str, Any] | None, drop: set[str] | None = None) -> dict[str, Any]:
    """``{"id", "type", "attributes": {...}}`` -> ``{"id": ..., <attributes with snake_case keys>}``."""
    if not resource:
        return {}
    out: dict[str, Any] = {"id": resource.get("id")}
    for key, value in (resource.get("attributes") or {}).items():
        name = key.replace("-", "_")
        if drop and name in drop:
            continue
        out[name] = value
    return out


def item(payload: dict[str, Any] | None, drop: set[str] | None = None) -> dict[str, Any]:
    data = (payload or {}).get("data")
    if isinstance(data, list):
        data = data[0] if data else None
    return flatten(data, drop)


def page(
    payload: dict[str, Any] | None,
    page_number: int,
    page_size: int,
    drop: set[str] | None = None,
    start: int | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    rows = payload.get("data") or []
    first = (page_number - 1) * page_size
    skip = max((start if start is not None else first) - first, 0)
    items = [flatten(r, drop) for r in rows[skip:]]
    meta = payload.get("meta") or {}
    total = meta.get("total-count")
    total_pages = meta.get("total-pages")
    if meta.get("next-page") is not None:
        has_more = True
    elif total_pages is not None:
        has_more = page_number < int(total_pages)
    elif total is not None:
        has_more = page_number * page_size < int(total)
    else:
        has_more = len(rows) >= page_size
    result: dict[str, Any] = {
        "items": items,
        "count": len(items),
        "page_number": page_number,
        "page_size": page_size,
        "has_more": has_more,
    }
    if total is not None:
        result["total_count"] = total
    # offset / next_offset continue exactly, also after a page is cut to fit the size limit.
    result["offset"] = first + skip
    if has_more:
        result["next_offset"] = first + len(rows)
    result["_resume"] = {"key": "next_offset", "start": first + skip}
    return result


def keep_matching(result: dict[str, Any], match: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    """Filter a page locally; a cut result then continues after the last match it returned."""
    start = result["offset"]
    kept = [(i, item) for i, item in enumerate(result["items"]) if match(item)]
    result["items"] = [item for _, item in kept]
    result["count"] = len(kept)
    result["_resume"] = {"key": "next_offset", "positions": [start + i + 1 for i, _ in kept]}
    return result


def attributes(type_: str, values: dict[str, Any], resource_id: Any = None) -> dict[str, Any]:
    """Build a JSON:API request document, dropping unset values and dasherizing keys."""
    attrs = {k.replace("_", "-"): v for k, v in values.items() if v is not None}
    data: dict[str, Any] = {"type": type_, "attributes": attrs}
    if resource_id is not None:
        data["id"] = str(resource_id)
    return {"data": data}
