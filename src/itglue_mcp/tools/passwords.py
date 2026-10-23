# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Password entries. Secrets are only returned by get_password and never echoed on writes."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import CREATE, READ, UPDATE, Offset, PageNumber, PageSize, ToolInputError, locate, run, seg

SECRET_FIELDS = {"password", "otp_secret"}

EntryName = Annotated[str | None, Field(description='Entry name, e.g. "Jane Doe - Microsoft 365".')]
Username = Annotated[str | None, Field(description="Username or login.")]
Url = Annotated[str | None, Field(description="Login URL.")]
Notes = Annotated[str | None, Field(description="Notes.")]
CategoryId = Annotated[int | None, Field(description="Password category ID.")]


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="search_passwords",
        description=(
            "Find password entries in IT Glue by organization, name, category, URL or username. "
            "Returns metadata only; use get_password to read a secret."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def search_passwords(
        organization_id: Annotated[int | None, Field(description="Organization ID.")] = None,
        name: Annotated[str | None, Field(description="Entry name to match.")] = None,
        password_category_id: CategoryId = None,
        url: Annotated[str | None, Field(description="URL to match.")] = None,
        username: Annotated[
            str | None,
            Field(description="Username to match (case-insensitive, applied to the returned page)."),
        ] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
        offset: Offset = None,
        sort: Annotated[
            str | None,
            Field(
                description="Sort field: name, username, url, id, created_at or updated_at. Prefix '-' for descending."
            ),
        ] = None,
    ) -> str:
        size, number, params, start = locate(page_size, page_number, offset)
        params.update(
            {
                "filter[organization_id]": organization_id,
                "filter[name]": name,
                "filter[password_category_id]": password_category_id,
                "filter[url]": url,
                "sort": sort,
            }
        )

        async def handler(client: api.ITGlueClient):
            result = api.page(await client.get("/passwords", params), number, size, drop=SECRET_FIELDS, start=start)
            if username:
                wanted = username.strip().lower()
                result["items"] = [i for i in result["items"] if wanted in str(i.get("username") or "").lower()]
                result["count"] = len(result["items"])
            return result

        return await run(settings, handler)

    @mcp.tool(
        name="get_password",
        description="Get one IT Glue password entry by ID, including the secret unless show_password is false.",
        annotations=READ,
        structured_output=False,
    )
    async def get_password(
        id: Annotated[str, Field(description="Password entry ID.")],
        show_password: Annotated[bool | None, Field(description="Include the secret value (default true).")] = True,
    ) -> str:
        reveal = show_password is not False

        async def handler(client: api.ITGlueClient):
            payload = await client.get(f"/passwords/{seg(id)}", {"show_password": str(reveal).lower()})
            return api.item(payload, drop=None if reveal else SECRET_FIELDS)

        return await run(settings, handler)

    @mcp.tool(
        name="create_password",
        description=(
            "Create a password entry in an IT Glue organization. To avoid duplicates, search_passwords "
            "first and use update_password if the entry exists. The secret is not echoed back."
        ),
        annotations=CREATE,
        structured_output=False,
    )
    async def create_password(
        organization_id: Annotated[int, Field(description="Organization that owns the entry.")],
        name: Annotated[str, Field(description='Entry name, e.g. "Jane Doe - Microsoft 365".')],
        password: Annotated[str, Field(description="The secret value.")],
        username: Username = None,
        url: Url = None,
        notes: Notes = None,
        password_category_id: CategoryId = None,
    ) -> str:
        values = dict(
            name=name,
            username=username,
            password=password,
            url=url,
            notes=notes,
            password_category_id=password_category_id,
        )

        async def handler(client: api.ITGlueClient):
            path = f"/organizations/{seg(organization_id)}/relationships/passwords"
            return api.item(await client.post(path, api.attributes("passwords", values)), drop=SECRET_FIELDS)

        return await run(settings, handler)

    @mcp.tool(
        name="update_password",
        description=(
            "Update an IT Glue password entry. Only the fields you pass are changed; the secret is not echoed back."
        ),
        annotations=UPDATE,
        structured_output=False,
    )
    async def update_password(
        organization_id: Annotated[int, Field(description="Organization that owns the entry.")],
        id: Annotated[str, Field(description="Password entry ID.")],
        name: EntryName = None,
        username: Username = None,
        password: Annotated[str | None, Field(description="New secret value.")] = None,
        url: Url = None,
        notes: Notes = None,
        password_category_id: CategoryId = None,
    ) -> str:
        values = dict(
            name=name,
            username=username,
            password=password,
            url=url,
            notes=notes,
            password_category_id=password_category_id,
        )

        async def handler(client: api.ITGlueClient):
            if not any(v is not None for v in values.values()):
                raise ToolInputError("Pass at least one field to change.")
            path = f"/organizations/{seg(organization_id)}/relationships/passwords/{seg(id)}"
            return api.item(await client.patch(path, api.attributes("passwords", values)), drop=SECRET_FIELDS)

        return await run(settings, handler)
