# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Password entries. Secrets are only returned by get_password and never echoed on writes.

Rotation (find an entry, then set a new secret): search_passwords -> update_password.
"""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import (
    CREATE,
    READ,
    SECRET_SCHEMA,
    UPDATE,
    Offset,
    PageNumber,
    PageSize,
    ToolInputError,
    locate,
    run,
    seg,
)

# Never returned by list or write tools. The list endpoint can include "password" on some entries.
SECRET_FIELDS = {"password", "otp_secret"}

EntryName = Annotated[str | None, Field(description='Entry name, e.g. "Jane Doe - Microsoft 365".')]
Username = Annotated[str | None, Field(description="Username or login.")]
Url = Annotated[str | None, Field(description="Login URL.")]
Notes = Annotated[str | None, Field(description="Notes.")]
CategoryId = Annotated[int | None, Field(description="Password category ID.")]
FolderId = Annotated[int | None, Field(description="Password folder ID (see list_password_folders).")]


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="search_passwords",
        description=(
            "Find password entries in IT Glue by organization, name, category, folder, URL or username. "
            "Returns metadata only (id, name, username, category, updated_at), never secrets; "
            "use get_password to read one or update_password to rotate it."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def search_passwords(
        organization_id: Annotated[int | None, Field(description="Organization ID.")] = None,
        name: Annotated[str | None, Field(description="Entry name to match.")] = None,
        password_category_id: CategoryId = None,
        password_folder_id: FolderId = None,
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
                "filter[password_folder_id]": password_folder_id,
                "filter[url]": url,
                "sort": sort,
            }
        )

        async def handler(client: api.ITGlueClient):
            result = api.page(await client.get("/passwords", params), number, size, drop=SECRET_FIELDS, start=start)
            if username:
                wanted = username.strip().lower()
                # IT Glue has no username filter, so it is matched on the fetched page.
                api.keep_matching(result, lambda i: wanted in str(i.get("username") or "").lower())
            return result

        return await run(settings, handler)

    @mcp.tool(
        name="list_password_folders",
        description=(
            "List the password folders of an IT Glue organization with their IDs, names and parent folder, "
            "e.g. to choose a folder for create_password."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def list_password_folders(
        organization_id: Annotated[int, Field(description="Organization ID.")],
        name: Annotated[
            str | None,
            Field(description="Text to match in the folder name (case-insensitive, applied to the returned page)."),
        ] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
        offset: Offset = None,
    ) -> str:
        size, number, params, start = locate(page_size, page_number, offset)

        async def handler(client: api.ITGlueClient):
            path = f"/organizations/{seg(organization_id)}/relationships/password_folders"
            result = api.page(await client.get(path, params), number, size, start=start)
            if name:
                wanted = name.strip().lower()
                api.keep_matching(result, lambda i: wanted in str(i.get("name") or "").lower())
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
            "Create a password entry in an IT Glue organization, optionally in a password folder "
            "(see list_password_folders). To avoid duplicates, search_passwords first and use "
            "update_password if the entry exists. The secret is not echoed back."
        ),
        annotations=CREATE,
        structured_output=False,
    )
    async def create_password(
        organization_id: Annotated[int, Field(description="Organization that owns the entry.")],
        name: Annotated[str, Field(description='Entry name, e.g. "Jane Doe - Microsoft 365".')],
        password: Annotated[str, Field(description="The secret value.", json_schema_extra=SECRET_SCHEMA)],
        username: Username = None,
        url: Url = None,
        notes: Notes = None,
        password_category_id: CategoryId = None,
        password_folder_id: FolderId = None,
    ) -> str:
        values = dict(
            name=name,
            username=username,
            password=password,
            url=url,
            notes=notes,
            password_category_id=password_category_id,
            password_folder_id=password_folder_id,
        )

        async def handler(client: api.ITGlueClient):
            path = f"/organizations/{seg(organization_id)}/relationships/passwords"
            if password_folder_id is not None:
                seg(password_folder_id)
            created = api.item(await client.post(path, api.attributes("passwords", values)), drop=SECRET_FIELDS)
            if password_folder_id is None or str(created.get("password_folder_id")) == str(password_folder_id):
                return created
            # PRD-22427: IT Glue may ignore the folder on create, so move the new entry with one follow-up update.
            try:
                moved = await client.patch(
                    f"/passwords/{seg(created.get('id'))}",
                    api.attributes("passwords", {"password_folder_id": password_folder_id}),
                    {"show_password": "false"},
                )
            except (api.ApiError, ToolInputError) as exc:
                # The entry exists: report it instead of an error so a retry does not create a duplicate.
                code = getattr(exc, "code", "invalid_argument")
                created["warning"] = (
                    f"Created at the organization's top level; moving it into folder {password_folder_id} "
                    f"failed: {code}. Use update_password with password_folder_id to move it."
                )
                return created
            return api.item(moved, drop=SECRET_FIELDS)

        return await run(settings, handler, secrets=[password])

    @mcp.tool(
        name="update_password",
        description=(
            "Update an IT Glue password entry, e.g. rotate its secret: find the entry ID with search_passwords, "
            "then pass id and the new password. Pass password_folder_id to move the entry into a folder. "
            "Only the fields you pass are changed; the secret is not echoed back."
        ),
        annotations=UPDATE,
        structured_output=False,
    )
    async def update_password(
        id: Annotated[str, Field(description="Password entry ID.")],
        organization_id: Annotated[
            int | None, Field(description="Organization that owns the entry (optional).")
        ] = None,
        name: EntryName = None,
        username: Username = None,
        password: Annotated[str | None, Field(description="New secret value.", json_schema_extra=SECRET_SCHEMA)] = None,
        url: Url = None,
        notes: Notes = None,
        password_category_id: CategoryId = None,
        password_folder_id: FolderId = None,
    ) -> str:
        values = dict(
            name=name,
            username=username,
            password=password,
            url=url,
            notes=notes,
            password_category_id=password_category_id,
            password_folder_id=password_folder_id,
        )

        async def handler(client: api.ITGlueClient):
            if not any(v is not None for v in values.values()):
                raise ToolInputError("Pass at least one field to change.")
            if organization_id is None:
                path = f"/passwords/{seg(id)}"
            else:
                path = f"/organizations/{seg(organization_id)}/relationships/passwords/{seg(id)}"
            payload = await client.patch(path, api.attributes("passwords", values), {"show_password": "false"})
            return api.item(payload, drop=SECRET_FIELDS)

        return await run(settings, handler, secrets=[password])
