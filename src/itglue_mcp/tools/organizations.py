# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Organizations (MSP clients) and the connectivity check."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import READ, PageNumber, PageSize, paging, run, seg


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="search_organizations",
        description=(
            "Find IT Glue organizations (client companies) by name, type, status or PSA ID. "
            "Returns id, name, type, status and PSA links; use the id with other tools."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def search_organizations(
        name: Annotated[str | None, Field(description="Organization name to match.")] = None,
        organization_type_id: Annotated[int | None, Field(description="Organization type ID.")] = None,
        organization_status_id: Annotated[int | None, Field(description="Organization status ID.")] = None,
        psa_id: Annotated[str | None, Field(description="ID of the organization in the linked PSA.")] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
        sort: Annotated[
            str | None,
            Field(description="Sort field, e.g. name, id, created_at, updated_at. Prefix '-' for descending."),
        ] = None,
    ) -> str:
        size, number, params = paging(page_size, page_number)
        params.update(
            {
                "filter[name]": name,
                "filter[organization_type_id]": organization_type_id,
                "filter[organization_status_id]": organization_status_id,
                "filter[psa_id]": psa_id,
                "sort": sort,
            }
        )

        async def handler(client: api.ITGlueClient):
            return api.page(await client.get("/organizations", params), number, size)

        return await run(settings, handler)

    @mcp.tool(
        name="get_organization",
        description="Get one IT Glue organization by ID, with its type, status, short name and quick notes.",
        annotations=READ,
        structured_output=False,
    )
    async def get_organization(
        id: Annotated[str, Field(description="Organization ID.")],
    ) -> str:
        async def handler(client: api.ITGlueClient):
            return api.item(await client.get(f"/organizations/{seg(id)}"))

        return await run(settings, handler)

    @mcp.tool(
        name="itglue_health_check",
        description="Check that the IT Glue API is reachable with the supplied API key and region.",
        annotations=READ,
        structured_output=False,
    )
    async def itglue_health_check() -> str:
        async def handler(client: api.ITGlueClient):
            await client.get("/organization_types", {"page[size]": 1})
            return {"status": "ok", "message": "IT Glue API is reachable and the API key was accepted."}

        return await run(settings, handler)
