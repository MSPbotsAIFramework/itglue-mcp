# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""User activity metrics (created / viewed / edited / deleted counts per day)."""

from datetime import date
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import READ, PageNumber, PageSize, ToolInputError, paging, run

MAX_RANGE_DAYS = 7


def date_filter(start_date: str | None, end_date: str | None) -> str | None:
    """Build IT Glue's ``filter[date]`` value ("start,end", "*" for an open side)."""
    if not start_date and not end_date:
        return None
    if end_date and not start_date:
        raise ToolInputError("end_date requires start_date.")
    try:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
    except ValueError as exc:
        raise ToolInputError("Dates must be YYYY-MM-DD.") from exc
    if start and end:
        if end < start:
            raise ToolInputError("end_date is before start_date.")
        if (end - start).days > MAX_RANGE_DAYS:
            raise ToolInputError(f"The date range may span at most {MAX_RANGE_DAYS} days.")
    return f"{start.isoformat() if start else '*'},{end.isoformat() if end else '*'}"


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="search_user_metrics",
        description=(
            "Get IT Glue user activity: per user, organization and resource type, how many records were "
            "created, viewed, edited and deleted each day (UTC). The date range may span at most 7 days."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def search_user_metrics(
        user_id: Annotated[int | None, Field(description="IT Glue user ID.")] = None,
        organization_id: Annotated[int | None, Field(description="Organization ID.")] = None,
        resource_type: Annotated[
            str | None,
            Field(description="Resource type, e.g. Configuration, Password, Document, FlexibleAsset."),
        ] = None,
        start_date: Annotated[str | None, Field(description="Start date (UTC), YYYY-MM-DD.")] = None,
        end_date: Annotated[str | None, Field(description="End date (UTC), YYYY-MM-DD. Requires start_date.")] = None,
        sort: Annotated[
            str | None,
            Field(description="Sort field: id, created, viewed, edited, deleted or date. Prefix '-' for descending."),
        ] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
    ) -> str:
        size, number, params = paging(page_size, page_number)

        async def handler(client: api.ITGlueClient):
            params.update(
                {
                    "filter[user_id]": user_id,
                    "filter[organization_id]": organization_id,
                    "filter[resource_type]": resource_type,
                    "filter[date]": date_filter(start_date, end_date),
                    "sort": sort,
                }
            )
            return api.page(await client.get("/user_metrics", params), number, size)

        return await run(settings, handler)
