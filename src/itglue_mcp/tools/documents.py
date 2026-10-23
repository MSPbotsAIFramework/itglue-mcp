# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Documents, their sections and folders.

A document body is a list of sections (text, heading, gallery, step). Edits to
sections only become visible after the document is published.
"""

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import _json, api
from ..config import Settings
from ._common import (
    CREATE,
    DESTRUCTIVE,
    DESTRUCTIVE_IDEMPOTENT,
    READ,
    UPDATE,
    Offset,
    PageNumber,
    PageSize,
    locate,
    run,
    seg,
)

SECTION_TYPES = {"heading": "Document::Heading", "text": "Document::Text"}
SECTION_FIELDS = ("resource_type", "level", "content", "sort", "duration", "created_at", "updated_at")
PUBLISH_HINT = "Call publish_document afterwards so the change becomes visible."
SECTIONS_PAGE = 50
SECTIONS_MAX = 200
SECTIONS_FETCH = 1000  # sections per request when reading a document's sections
CONTENT_CHUNK = 12_000  # characters of one section's content per call

SectionOffset = Annotated[
    int | None, Field(description="Section position to start from (0-based); pass next_offset.", ge=0)
]
SectionLimit = Annotated[
    int | None, Field(description=f"Sections to return (default {SECTIONS_PAGE}, max {SECTIONS_MAX}).", ge=1)
]

DocumentId = Annotated[int, Field(description="Document ID.")]
LooseDocumentId = Annotated[int | str, Field(description="Document ID (a numeric string is accepted).")]


def _sections_path(document_id: object) -> str:
    return f"/documents/{seg(document_id)}/relationships/sections"


def _section(raw: dict[str, Any]) -> dict[str, Any]:
    flat = api.flatten(raw)
    return {"id": flat.get("id"), **{k: flat[k] for k in SECTION_FIELDS if flat.get(k) is not None}}


async def _all_sections(client: api.ITGlueClient, document_id: object) -> list[dict[str, Any]]:
    """Every section: the endpoint pages 50 at a time by default (a 66-section document returned 50)."""
    rows: list[dict[str, Any]] = []
    number = 1
    while True:
        params = {"page[size]": SECTIONS_FETCH, "page[number]": number}
        payload = await client.get(_sections_path(document_id), params) or {}
        rows += payload.get("data") or []
        following = (payload.get("meta") or {}).get("next-page")
        if not following or number >= 100:
            return rows
        number = int(following)


def _section_page(sections: list[dict[str, Any]], offset: int | None, limit: int | None) -> dict[str, Any]:
    """One page of a document's sections. content_length shows when a section's content was shortened."""
    start = offset or 0
    size = min(limit or SECTIONS_PAGE, SECTIONS_MAX)
    page = [s | {"content_length": len(str(s.get("content") or ""))} for s in sections[start : start + size]]
    end = start + len(page)
    result: dict[str, Any] = {"items": page, "count": len(page), "total_count": len(sections), "offset": start}
    result["has_more"] = end < len(sections)
    if result["has_more"]:
        result["next_offset"] = end
    result["_resume"] = {"key": "next_offset", "start": start}
    return result


def _section_part(sections: list[dict[str, Any]], section_id: int, content_offset: int | None) -> dict[str, Any]:
    """One section with a slice of its content, sized to fit the response limit."""
    section = next((s for s in sections if str(s.get("id")) == str(section_id)), None)
    if section is None:
        raise api.ApiError("not_found", f"The document has no section {section_id}.")
    content = str(section.get("content") or "")
    start = min(content_offset or 0, len(content))
    chunk = CONTENT_CHUNK
    while True:
        end = min(start + chunk, len(content))
        result: dict[str, Any] = {
            "section": section | {"content": content[start:end]},
            "content_offset": start,
            "content_length": len(content),
            "has_more": end < len(content),
        }
        if result["has_more"]:
            result["next_content_offset"] = end
        if len(_json.compact(result)) <= _json.MAX_CHARS - 200 or chunk <= 500:
            return result
        chunk = chunk * 3 // 4  # escaped HTML can be longer than its character count


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
        offset: Offset = None,
        sort: Annotated[str | None, Field(description="Sort field. Prefix '-' for descending.")] = None,
        document_folder_id: Annotated[
            int | None,
            Field(description="Only documents in this folder. Omit for documents in all folders; 0 for root only."),
        ] = None,
    ) -> str:
        size, number, params, start = locate(page_size, page_number, offset)
        params["filter[document_folder_id]"] = "null" if document_folder_id is None else document_folder_id
        params["sort"] = sort

        async def handler(client: api.ITGlueClient):
            path = f"/organizations/{seg(organization_id)}/relationships/documents"
            result = api.page(await client.get(path, params), number, size, drop={"content"}, start=start)
            if name:
                wanted = name.strip().lower()
                api.keep_matching(result, lambda i: wanted in str(i.get("name") or "").lower())
            return result

        return await run(settings, handler)

    @mcp.tool(
        name="get_document",
        description=(
            "Get an IT Glue document with its sections in order (headings and HTML text). Long documents are "
            "paged: pass next_offset. A section whose content_length is larger than its content was shortened; "
            "read it in full with list_document_sections(section_id, content_offset)."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def get_document(
        organization_id: Annotated[int, Field(description="Organization that owns the document.")],
        id: Annotated[str, Field(description="Document ID.")],
        offset: SectionOffset = None,
        limit: SectionLimit = None,
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
            return {"document": document, **_section_page(sections, offset, limit)}

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
        offset: Offset = None,
    ) -> str:
        size, number, params, start = locate(page_size, page_number, offset)

        async def handler(client: api.ITGlueClient):
            path = f"/organizations/{seg(organization_id)}/relationships/document_folders"
            result = api.page(await client.get(path, params), number, size, start=start)
            if name:
                wanted = name.strip().lower()
                api.keep_matching(result, lambda i: wanted in str(i.get("name") or "").lower())
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
        description=(
            "List the sections of an IT Glue document in order, with their IDs. Read this before editing. "
            "Paged with offset / limit. With section_id it returns that one section, its content read in "
            "parts: pass next_content_offset as content_offset until has_more is false."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def list_document_sections(
        document_id: DocumentId,
        offset: SectionOffset = None,
        limit: SectionLimit = None,
        section_id: Annotated[
            int | None, Field(description="Return only this section, with its content read in parts.")
        ] = None,
        content_offset: Annotated[
            int | None, Field(description="With section_id: content position to read from (0-based).", ge=0)
        ] = None,
    ) -> str:
        async def handler(client: api.ITGlueClient):
            sections = [_section(s) for s in await _all_sections(client, document_id)]
            if section_id is not None:
                return _section_part(sections, section_id, content_offset)
            return _section_page(sections, offset, limit)

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
