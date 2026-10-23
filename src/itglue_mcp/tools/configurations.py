# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Configurations: devices and other assets documented per organization."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import READ, UPDATE, Offset, PageNumber, PageSize, locate, run, seg

SYNC_NOTE = "Records synced from a PSA or RMM may be changed back by the next sync; change the source system first."


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="search_configurations",
        description=(
            "Find configurations (devices and assets such as servers, workstations, firewalls) in IT Glue. "
            "Filter by organization, name, type, status, serial number, RMM ID or PSA ID."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def search_configurations(
        organization_id: Annotated[int | None, Field(description="Organization ID.")] = None,
        name: Annotated[str | None, Field(description="Configuration name to match.")] = None,
        configuration_type_id: Annotated[int | None, Field(description="Configuration type ID.")] = None,
        configuration_status_id: Annotated[int | None, Field(description="Configuration status ID.")] = None,
        serial_number: Annotated[str | None, Field(description="Serial number.")] = None,
        rmm_id: Annotated[str | None, Field(description="ID of the device in the linked RMM.")] = None,
        psa_id: Annotated[str | None, Field(description="ID of the device in the linked PSA.")] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
        offset: Offset = None,
        sort: Annotated[
            str | None,
            Field(description="Sort field: name, id, created_at or updated_at. Prefix '-' for descending."),
        ] = None,
    ) -> str:
        size, number, params, start = locate(page_size, page_number, offset)
        params.update(
            {
                "filter[organization_id]": organization_id,
                "filter[name]": name,
                "filter[configuration_type_id]": configuration_type_id,
                "filter[configuration_status_id]": configuration_status_id,
                "filter[serial_number]": serial_number,
                "filter[rmm_id]": rmm_id,
                "filter[psa_id]": psa_id,
                "sort": sort,
            }
        )

        async def handler(client: api.ITGlueClient):
            return api.page(await client.get("/configurations", params), number, size, start=start)

        return await run(settings, handler)

    @mcp.tool(
        name="get_configuration",
        description="Get one IT Glue configuration (device or asset) by ID with all of its fields.",
        annotations=READ,
        structured_output=False,
    )
    async def get_configuration(
        id: Annotated[str, Field(description="Configuration ID.")],
    ) -> str:
        async def handler(client: api.ITGlueClient):
            return api.item(await client.get(f"/configurations/{seg(id)}"))

        return await run(settings, handler)

    async def _set_archived(configuration_id: int, archived: bool) -> str:
        async def handler(client: api.ITGlueClient):
            cid = seg(configuration_id)
            body = api.attributes("configurations", {"archived": archived})
            result = api.item(await client.patch(f"/configurations/{cid}", body))
            return {"id": result.get("id", cid), "name": result.get("name"), "archived": result.get("archived")}

        return await run(settings, handler)

    @mcp.tool(
        name="archive_configuration",
        description=(
            "Archive an IT Glue configuration. It is hidden from normal views but can be restored with "
            f"unarchive_configuration. {SYNC_NOTE} Confirm with the user first."
        ),
        annotations=UPDATE,
        structured_output=False,
    )
    async def archive_configuration(
        configuration_id: Annotated[int, Field(description="Configuration ID to archive.")],
    ) -> str:
        return await _set_archived(configuration_id, True)

    @mcp.tool(
        name="unarchive_configuration",
        description=(
            "Restore an archived IT Glue configuration so it shows in normal views again. "
            f"{SYNC_NOTE} Confirm with the user first."
        ),
        annotations=UPDATE,
        structured_output=False,
    )
    async def unarchive_configuration(
        configuration_id: Annotated[int, Field(description="Configuration ID to restore.")],
    ) -> str:
        return await _set_archived(configuration_id, False)
