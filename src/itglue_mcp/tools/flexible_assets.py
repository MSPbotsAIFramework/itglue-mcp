# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Flexible assets: custom record types defined per IT Glue account."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import READ, PageNumber, PageSize, paging, run

TYPES_PAGE_SIZE = 200


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="list_flexible_asset_types",
        description=(
            "List the flexible asset types defined in IT Glue (custom record types such as Active Directory "
            "or Wireless). Call this first to get the type ID for search_flexible_assets."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def list_flexible_asset_types(
        organization_id: Annotated[
            int | None,
            Field(description="Accepted for compatibility; types are defined account-wide, so it is ignored."),
        ] = None,
    ) -> str:
        async def handler(client: api.ITGlueClient):
            params = {"page[size]": TYPES_PAGE_SIZE, "page[number]": 1, "sort": "name"}
            return api.page(await client.get("/flexible_asset_types", params), 1, TYPES_PAGE_SIZE)

        return await run(settings, handler)

    @mcp.tool(
        name="search_flexible_assets",
        description=(
            "Find flexible assets of one type (get the type ID from list_flexible_asset_types), "
            "optionally for one organization or by exact name. Returns each asset's fields (traits)."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def search_flexible_assets(
        flexible_asset_type_id: Annotated[int, Field(description="Flexible asset type ID.")],
        organization_id: Annotated[int | None, Field(description="Organization ID.")] = None,
        name: Annotated[str | None, Field(description="Exact asset name.")] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
        sort: Annotated[
            str | None,
            Field(description="Sort field: name, created_at or updated_at. Prefix '-' for descending."),
        ] = None,
    ) -> str:
        size, number, params = paging(page_size, page_number)
        params.update(
            {
                "filter[flexible_asset_type_id]": flexible_asset_type_id,
                "filter[organization_id]": organization_id,
                "filter[name]": name,
                "sort": sort,
            }
        )

        async def handler(client: api.ITGlueClient):
            return api.page(await client.get("/flexible_assets", params), number, size)

        return await run(settings, handler)
