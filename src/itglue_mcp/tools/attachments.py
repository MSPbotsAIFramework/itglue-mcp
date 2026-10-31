# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""File attachments on IT Glue records."""

import base64
import binascii
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import CREATE, DESTRUCTIVE, READ, ToolInputError, run, seg

ResourceType = Literal[
    "checklists",
    "checklist_templates",
    "configurations",
    "contacts",
    "documents",
    "domains",
    "flexible_assets",
    "locations",
    "passwords",
    "ssl_certificates",
    "tickets",
]
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="create_attachment",
        description=(
            "Attach a file to an IT Glue record. Also the way to put an image in a document: upload it here, "
            "then use the returned download_url in an <img src>. Send the file as plain base64 (no data: prefix)."
        ),
        annotations=CREATE,
        structured_output=False,
    )
    async def create_attachment(
        resource_type: Annotated[ResourceType, Field(description="Kind of record to attach the file to.")],
        resource_id: Annotated[int, Field(description="ID of that record.")],
        file_name: Annotated[str, Field(description="File name with extension, e.g. network-diagram.png.")],
        content: Annotated[str, Field(description="File contents as base64, without a data: prefix.")],
    ) -> str:
        async def handler(client: api.ITGlueClient):
            data = content.strip()
            if data.startswith("data:") and "," in data:
                data = data.split(",", 1)[1]
            try:
                raw = base64.b64decode(data, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ToolInputError("content must be valid base64.") from exc
            if len(raw) > MAX_ATTACHMENT_BYTES:
                raise ToolInputError("File is larger than 10 MB.")
            body = {
                "data": {
                    "type": "attachments",
                    "attributes": {"attachment": {"content": data, "file_name": file_name}},
                }
            }
            path = f"/{resource_type}/{seg(resource_id)}/relationships/attachments"
            return api.item(await client.post(path, body))

        return await run(settings, handler)

    @mcp.tool(
        name="list_attachments",
        description="List the files attached to an IT Glue record, with their download URLs.",
        annotations=READ,
        structured_output=False,
    )
    async def list_attachments(
        resource_type: Annotated[ResourceType, Field(description="Kind of record.")],
        resource_id: Annotated[int, Field(description="ID of that record.")],
    ) -> str:
        async def handler(client: api.ITGlueClient):
            payload = await client.get(f"/{resource_type}/{seg(resource_id)}/relationships/attachments")
            items = [api.flatten(r) for r in (payload or {}).get("data") or []]
            return {"items": items, "count": len(items)}

        return await run(settings, handler)

    @mcp.tool(
        name="delete_attachment",
        description=(
            "Remove a file attachment from an IT Glue record (detach it). This cannot be undone; "
            "confirm with the user first."
        ),
        annotations=DESTRUCTIVE,
        structured_output=False,
    )
    async def delete_attachment(
        resource_type: Annotated[ResourceType, Field(description="Kind of record the attachment is on.")],
        resource_id: Annotated[int, Field(description="ID of that record.")],
        attachment_id: Annotated[int, Field(description="ID of the attachment relationship to remove.")],
    ) -> str:
        async def handler(client: api.ITGlueClient):
            aid = seg(attachment_id)
            body = {"data": [{"type": "attachments", "attributes": {"id": int(aid)}}]}
            await client.delete(f"/{resource_type}/{seg(resource_id)}/relationships/attachments", body)
            return {"id": aid, "deleted": True}

        return await run(settings, handler)
