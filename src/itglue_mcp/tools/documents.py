# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Documents, their sections and folders.

A document body is a list of sections (text, heading, gallery, step). Edits to
sections only become visible after the document is published.
"""

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import (
    CREATE,
    DESTRUCTIVE,
    DESTRUCTIVE_IDEMPOTENT,
    READ,
    UPDATE,
    PageNumber,
    PageSize,
    paging,
    run,
    seg,
)

SECTION_TYPES = {"heading": "Document::Heading", "text": "Document::Text"}
SECTION_FIELDS = ("resource_type", "level", "content", "sort", "duration", "created_at", "updated_at")
PUBLISH_HINT = "Call publish_document afterwards so the change becomes visible."

DocumentId = Annotated[int, Field(description="Document ID.")]
LooseDocumentId = Annotated[int | str, Field(description="Document ID (a numeric string is accepted).")]


def _sections_path(document_id: object) -> str:
    return f"/documents/{seg(document_id)}/relationships/sections"


def _section(raw: dict[str, Any]) -> dict[str, Any]:
    flat = api.flatten(raw)
    return {"id": flat.get("id"), **{k: flat[k] for k in SECTION_FIELDS if flat.get(k) is not None}}


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="search_documents",
        description=(
            "List documents of an IT Glue organization, optionally within one folder or by name. "
            "Returns metadata only (name, folder, URL, dates); use get_document for the content."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def search_documents(
        organization_id: Annotated[int, Field(description="Organization ID (documents belong to organizations).")],
        name: Annotated[
            str | None,
            Field(description="Text to match in the document name (case-insensitive, applied to the returned page)."),
        ] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
        sort: Annotated[str | None, Field(description="Sort field. Prefix '-' for descending.")] = None,
        document_folder_id: Annotated[
            int | None,
            Field(description="Only documents in this folder. Omit for documents in all folders; 0 for root only."),
        ] = None,
    ) -> str:
        size, number, params = paging(page_size, page_number)
        params["filter[document_folder_id]"] = "null" if document_folder_id is None else document_folder_id
        params["sort"] = sort

        async def handler(client: api.ITGlueClient):
            path = f"/organizations/{seg(organization_id)}/relationships/documents"
            result = api.page(await client.get(path, params), number, size, drop={"content"})
            if name:
                wanted = name.strip().lower()
                result["items"] = [i for i in result["items"] if wanted in str(i.get("name") or "").lower()]
                result["count"] = len(result["items"])
            return result

        return await run(settings, handler)

    @mcp.tool(
        name="get_document",
        description="Get an IT Glue document with all of its sections in order (headings and HTML text).",
        annotations=READ,
        structured_output=False,
    )
    async def get_document(
        organization_id: Annotated[int, Field(description="Organization that owns the document.")],
        id: Annotated[str, Field(description="Document ID.")],
    ) -> str:
        async def handler(client: api.ITGlueClient):
            path = f"/organizations/{seg(organization_id)}/relationships/documents/{seg(id)}"
            payload = await client.get(path)
            data = (payload or {}).get("data") or {}
            raw_sections = (data.get("attributes") or {}).get("sections") or []
            document = api.flatten(data, drop={"content", "sections"})
            sections = [
                _section({"id": s.get("id"), "attributes": s.get("attributes", s)})
                for s in raw_sections
                if isinstance(s, dict)
            ]
            return {"document": document, "items": sections, "count": len(sections)}

        return await run(settings, handler)

    @mcp.tool(
        name="list_document_folders",
        description=(
            "List the document folders of an IT Glue organization with their names and IDs, "
            "e.g. to choose a folder for create_document."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def list_document_folders(
        organization_id: Annotated[int, Field(description="Organization ID.")],
        name: Annotated[
            str | None,
            Field(description="Text to match in the folder name (case-insensitive, applied to the returned page)."),
        ] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
    ) -> str:
        size, number, params = paging(page_size, page_number)

        async def handler(client: api.ITGlueClient):
            path = f"/organizations/{seg(organization_id)}/relationships/document_folders"
            result = api.page(await client.get(path, params), number, size)
            if name:
                wanted = name.strip().lower()
                result["items"] = [i for i in result["items"] if wanted in str(i.get("name") or "").lower()]
                result["count"] = len(result["items"])
            return result

        return await run(settings, handler)

    @mcp.tool(
        name="create_document",
        description=(
            "Create a document in an IT Glue organization, optionally in a folder (see list_document_folders). "
            "If content is given it becomes the first text section and the document is published. "
            "Without document_folder_id the document is created at the organization root."
        ),
        annotations=CREATE,
        structured_output=False,
    )
    async def create_document(
        organization_id: Annotated[int, Field(description="Organization to create the document in.")],
        name: Annotated[str, Field(description="Document title.")],
        content: Annotated[str | None, Field(description="Initial body as HTML (optional).")] = None,
        document_folder_id: Annotated[int | None, Field(description="Folder to place the document in.")] = None,
        skip_folder_prompt: Annotated[
            bool | None,
            Field(description="Kept for compatibility; documents without a folder always go to the root."),
        ] = None,
    ) -> str:
        async def handler(client: api.ITGlueClient):
            org = seg(organization_id)
            if document_folder_id is not None:
                seg(document_folder_id)
            body = api.attributes("documents", {"name": name, "document_folder_id": document_folder_id})
            document = api.item(await client.post(f"/organizations/{org}/relationships/documents", body))
            doc_id = document.get("id")
            result: dict[str, Any] = {"document": document}
            if content and doc_id:
                section_body = api.attributes(
                    "document-sections", {"resource_type": SECTION_TYPES["text"], "content": content}
                )
                section = await client.post(_sections_path(doc_id), section_body)
                result["section"] = _section((section or {}).get("data") or {})
                await client.patch(f"/documents/{seg(doc_id)}/publish")
                result["published"] = True
            return result

        return await run(settings, handler)

    @mcp.tool(
        name="update_document",
        description=(
            "Rename an IT Glue document. It does not change the body (use the section tools) "
            "and cannot move the document to another folder."
        ),
        annotations=UPDATE,
        structured_output=False,
    )
    async def update_document(
        document_id: LooseDocumentId,
        name: Annotated[str, Field(description="New document title.")],
    ) -> str:
        async def handler(client: api.ITGlueClient):
            body = api.attributes("documents", {"name": name})
            return api.item(await client.patch(f"/documents/{seg(document_id)}", body), drop={"content"})

        return await run(settings, handler)

    @mcp.tool(
        name="delete_document",
        description=(
            "Permanently delete an IT Glue document and all of its sections. This cannot be undone; "
            "prefer archive_document. Confirm with the user first."
        ),
        annotations=DESTRUCTIVE,
        structured_output=False,
    )
    async def delete_document(document_id: LooseDocumentId) -> str:
        async def handler(client: api.ITGlueClient):
            doc = seg(document_id)
            body = {"data": [{"type": "documents", "attributes": {"id": int(doc)}}]}
            await client.delete("/documents", body)
            return {"id": doc, "deleted": True}

        return await run(settings, handler)

    @mcp.tool(
        name="list_document_sections",
        description="List the sections of an IT Glue document in order, with their IDs. Read this before editing.",
        annotations=READ,
        structured_output=False,
    )
    async def list_document_sections(document_id: DocumentId) -> str:
        async def handler(client: api.ITGlueClient):
            payload = await client.get(_sections_path(document_id))
            sections = [_section(s) for s in (payload or {}).get("data") or []]
            return {"items": sections, "count": len(sections)}

        return await run(settings, handler)

    @mcp.tool(
        name="create_document_section",
        description=f"Add a heading or text section to the end of an IT Glue document. {PUBLISH_HINT}",
        annotations=CREATE,
        structured_output=False,
    )
    async def create_document_section(
        document_id: DocumentId,
        section_type: Annotated[
            Literal["heading", "text"], Field(description="'heading' for a heading, 'text' for an HTML block.")
        ],
        content: Annotated[str, Field(description="Heading text, or HTML for a text section.")],
        level: Annotated[
            int | None, Field(description="Heading level 1-6 (headings only, default 2).", ge=1, le=6)
        ] = None,
    ) -> str:
        values: dict[str, Any] = {"resource_type": SECTION_TYPES[section_type], "content": content}
        if section_type == "heading":
            values["level"] = level or 2

        async def handler(client: api.ITGlueClient):
            payload = await client.post(_sections_path(document_id), api.attributes("document-sections", values))
            return _section((payload or {}).get("data") or {})

        return await run(settings, handler)

    @mcp.tool(
        name="update_document_section",
        description=(
            f"Replace the content of a section of an IT Glue document (IDs from list_document_sections). {PUBLISH_HINT}"
        ),
        annotations=UPDATE,
        structured_output=False,
    )
    async def update_document_section(
        document_id: DocumentId,
        section_id: Annotated[int, Field(description="Section ID from list_document_sections.")],
        content: Annotated[str, Field(description="New heading text or HTML.")],
    ) -> str:
        async def handler(client: api.ITGlueClient):
            path = f"{_sections_path(document_id)}/{seg(section_id)}"
            payload = await client.patch(path, api.attributes("document-sections", {"content": content}))
            return _section((payload or {}).get("data") or {})

        return await run(settings, handler)

    @mcp.tool(
        name="delete_document_section",
        description=(
            f"Permanently delete a section from an IT Glue document. This cannot be undone. {PUBLISH_HINT} "
            "Confirm with the user first."
        ),
        annotations=DESTRUCTIVE,
        structured_output=False,
    )
    async def delete_document_section(
        document_id: DocumentId,
        section_id: Annotated[int, Field(description="Section ID from list_document_sections.")],
    ) -> str:
        async def handler(client: api.ITGlueClient):
            await client.delete(f"{_sections_path(document_id)}/{seg(section_id)}")
            return {"document_id": str(document_id), "section_id": str(section_id), "deleted": True}

        return await run(settings, handler)

    @mcp.tool(
        name="publish_document",
        description="Publish an IT Glue document so section changes become visible. Call after editing sections.",
        annotations=UPDATE,
        structured_output=False,
    )
    async def publish_document(document_id: DocumentId) -> str:
        async def handler(client: api.ITGlueClient):
            doc = api.item(await client.patch(f"/documents/{seg(document_id)}/publish"), drop={"content"})
            return {
                "id": doc.get("id", str(document_id)),
                "name": doc.get("name"),
                "published_at": doc.get("published_at"),
                "resource_url": doc.get("resource_url"),
            }

        return await run(settings, handler)

    async def _set_archived(document_id: int, archived: bool) -> str:
        async def handler(client: api.ITGlueClient):
            body = api.attributes("documents", {"archived": archived})
            doc = api.item(await client.patch(f"/documents/{seg(document_id)}", body), drop={"content"})
            return {"id": doc.get("id", str(document_id)), "name": doc.get("name"), "archived": doc.get("archived")}

        return await run(settings, handler)

    @mcp.tool(
        name="archive_document",
        description=(
            "Archive an IT Glue document. It is hidden from normal views but can be restored with "
            "unarchive_document. Confirm with the user first."
        ),
        annotations=DESTRUCTIVE_IDEMPOTENT,
        structured_output=False,
    )
    async def archive_document(document_id: Annotated[int, Field(description="Document ID to archive.")]) -> str:
        return await _set_archived(document_id, True)

    @mcp.tool(
        name="unarchive_document",
        description="Restore an archived IT Glue document so all users see it again. Confirm with the user first.",
        annotations=DESTRUCTIVE_IDEMPOTENT,
        structured_output=False,
    )
    async def unarchive_document(document_id: Annotated[int, Field(description="Document ID to restore.")]) -> str:
        return await _set_archived(document_id, False)
