# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Account users (the IT Glue account's own user directory, not per-user activity metrics)."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import READ, Offset, PageNumber, PageSize, locate, run


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="itglue_list_account_users",
        description=(
            "List the users in this IT Glue account: id, name, email, role, My Glue flag and last "
            "sign-in time. Use this for license counting and user audits; for per-user activity "
            "counts use search_user_metrics instead."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def itglue_list_account_users(
        name: Annotated[str | None, Field(description="User name to match (exact match per IT Glue's API).")] = None,
        email: Annotated[str | None, Field(description="Email address to match.")] = None,
        role_name: Annotated[str | None, Field(description="Role name to match, e.g. Administrator.")] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
        offset: Offset = None,
        sort: Annotated[
            str | None,
            Field(
                description="Sort field: name, email, reputation, id, created_at or updated_at. "
                "Prefix '-' for descending."
            ),
        ] = None,
    ) -> str:
        size, number, params, start = locate(page_size, page_number, offset)
        params.update(
            {
                "filter[name]": name,
                "filter[email]": email,
                "filter[role_name]": role_name,
                "sort": sort,
            }
        )

        async def handler(client: api.ITGlueClient):
            return api.page(await client.get("/users", params), number, size, start=start)

        return await run(settings, handler)
