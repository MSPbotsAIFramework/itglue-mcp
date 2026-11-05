# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Contacts (people at an organization) — read-only (PRD-21625)."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import READ, Offset, PageNumber, PageSize, locate, run


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="itglue_list_contacts",
        description=(
            "List IT Glue contacts (people at an organization), filtered by organization, email, "
            "name or contact type. Use this to map an external identity (e.g. an M365 mailbox) to "
            "its IT Glue contact: pass organization_id and email."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def itglue_list_contacts(
        organization_id: Annotated[str | None, Field(description="Organization ID to filter by.")] = None,
        email: Annotated[str | None, Field(description="Email address to match.")] = None,
        name: Annotated[str | None, Field(description="Full name to match.")] = None,
        first_name: Annotated[str | None, Field(description="First name to match.")] = None,
        last_name: Annotated[str | None, Field(description="Last name to match.")] = None,
        contact_type_id: Annotated[str | None, Field(description="Contact type ID to filter by.")] = None,
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
                "filter[email]": email,
                "filter[name]": name,
                "filter[first_name]": first_name,
                "filter[last_name]": last_name,
                "filter[contact_type_id]": contact_type_id,
                "sort": sort,
            }
        )

        async def handler(client: api.ITGlueClient):
            return api.page(await client.get("/contacts", params), number, size, start=start)

        return await run(settings, handler)
