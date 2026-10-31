# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Flexible assets: custom record types defined per IT Glue account."""

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import CREATE, READ, UPDATE, Offset, PageNumber, PageSize, ToolInputError, locate, run, seg

TYPES_PAGE_SIZE = 200

Name = Annotated[str | None, Field(description="Flexible asset name.")]
Traits = Annotated[
    dict[str, Any] | None,
    Field(description="Trait values keyed by the flexible asset type's field name (account-specific)."),
]


def _trait_secrets(traits: dict[str, Any] | None) -> list[str]:
    # Traits are opaque, account-defined custom fields; any string value in them is treated as
    # potentially sensitive and masked from error messages/logs, same posture as a password field.
    return [v for v in (traits or {}).values() if isinstance(v, str)]


def _field_relationship_item(field: dict[str, Any], index: int) -> dict[str, Any]:
    """One `flexible-asset-fields` relationship item, validated before any HTTP call (AC5)."""
    if not isinstance(field, dict) or not field.get("name"):
        raise ToolInputError(f"fields[{index}] is missing required 'name'.")
    if not field.get("kind"):
        raise ToolInputError(f"fields[{index}] is missing required 'kind'.")
    attrs = {k.replace("_", "-"): v for k, v in field.items() if v is not None}
    return {"type": "flexible_asset_fields", "attributes": attrs}


def _field_secrets(fields: list[dict[str, Any]] | None) -> list[str]:
    # A field's default_value can carry a secret (e.g. a Password-kind field's default), same
    # posture as a trait value.
    out = []
    for f in fields or []:
        value = f.get("default_value") if isinstance(f, dict) else None
        if isinstance(value, str):
            out.append(value)
    return out


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
        offset: Offset = None,
    ) -> str:
        async def handler(client: api.ITGlueClient):
            size, number, params, start = locate(None, None, offset, fixed_size=TYPES_PAGE_SIZE)
            params["sort"] = "name"
            return api.page(await client.get("/flexible_asset_types", params), number, size, start=start)

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
        offset: Offset = None,
        sort: Annotated[
            str | None,
            Field(description="Sort field: name, created_at or updated_at. Prefix '-' for descending."),
        ] = None,
    ) -> str:
        size, number, params, start = locate(page_size, page_number, offset)
        params.update(
            {
                "filter[flexible_asset_type_id]": flexible_asset_type_id,
                "filter[organization_id]": organization_id,
                "filter[name]": name,
                "sort": sort,
            }
        )

        async def handler(client: api.ITGlueClient):
            return api.page(await client.get("/flexible_assets", params), number, size, start=start)

        return await run(settings, handler)

    @mcp.tool(
        name="get_flexible_asset",
        description="Get one IT Glue flexible asset (custom record) by ID, including its trait values.",
        annotations=READ,
        structured_output=False,
    )
    async def get_flexible_asset(id: Annotated[str, Field(description="Flexible asset ID.")]) -> str:
        async def handler(client: api.ITGlueClient):
            return api.item(await client.get(f"/flexible_assets/{seg(id)}"))

        return await run(settings, handler)

    @mcp.tool(
        name="create_flexible_asset",
        description=(
            "Create a flexible asset (custom record) of a given type in an IT Glue organization. "
            "Get the type ID from list_flexible_asset_types; traits are that type's custom fields."
        ),
        annotations=CREATE,
        structured_output=False,
    )
    async def create_flexible_asset(
        organization_id: Annotated[int, Field(description="Organization that owns the asset.")],
        flexible_asset_type_id: Annotated[int, Field(description="Flexible asset type ID.")],
        name: Name = None,
        traits: Traits = None,
        archived: Annotated[bool | None, Field(description="Archived flag.")] = None,
        restricted: Annotated[bool | None, Field(description="Restricted (MyGlue-visibility) flag.")] = None,
    ) -> str:
        values = dict(
            organization_id=organization_id,
            flexible_asset_type_id=flexible_asset_type_id,
            name=name,
            traits=traits,
            archived=archived,
            restricted=restricted,
        )

        async def handler(client: api.ITGlueClient):
            return api.item(await client.post("/flexible_assets", api.attributes("flexible_assets", values)))

        return await run(settings, handler, secrets=_trait_secrets(traits))

    @mcp.tool(
        name="update_flexible_asset",
        description=(
            "Update an IT Glue flexible asset. Only the fields you pass are changed; IT Glue merges "
            "posted traits into the existing trait values rather than replacing them wholesale."
        ),
        annotations=UPDATE,
        structured_output=False,
    )
    async def update_flexible_asset(
        id: Annotated[str, Field(description="Flexible asset ID.")],
        name: Name = None,
        traits: Traits = None,
        archived: Annotated[bool | None, Field(description="Archived flag.")] = None,
    ) -> str:
        values = dict(name=name, traits=traits, archived=archived)

        async def handler(client: api.ITGlueClient):
            if not any(v is not None for v in values.values()):
                raise ToolInputError("Pass at least one field to change.")
            path = f"/flexible_assets/{seg(id)}"
            return api.item(await client.patch(path, api.attributes("flexible_assets", values)))

        return await run(settings, handler, secrets=_trait_secrets(traits))

    @mcp.tool(
        name="itglue_create_flexible_asset_type",
        description=(
            "Create a flexible asset type (a custom record type, e.g. 'BitLocker (Rewst)') in IT Glue, "
            "optionally together with its field definitions in the same call."
        ),
        annotations=CREATE,
        structured_output=False,
    )
    async def itglue_create_flexible_asset_type(
        name: Annotated[str, Field(description="Flexible asset type name.")],
        enabled: Annotated[bool | None, Field(description="Whether the type is enabled.")] = None,
        description: Annotated[str | None, Field(description="Type description.")] = None,
        icon: Annotated[str | None, Field(description="IT Glue icon name.")] = None,
        fields: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Fields to create with the type. Each item needs 'name' and 'kind' (e.g. Text, "
                    "Textbox, Password, Tag, Checkbox, Date, Number -- not validated locally, IT Glue "
                    "rejects an invalid value); optional per field: order, required, show_in_list, "
                    "use_for_title, tag_type, hint, default_value."
                )
            ),
        ] = None,
    ) -> str:
        type_values = dict(name=name, enabled=enabled, description=description, icon=icon)

        async def handler(client: api.ITGlueClient):
            field_items = [_field_relationship_item(f, i) for i, f in enumerate(fields or [])]
            relationships = {"flexible-asset-fields": field_items} if field_items else None
            body = api.attributes("flexible_asset_types", type_values, relationships=relationships)
            resp = await client.post("/flexible_asset_types", body)
            result = api.item(resp)
            created = (((resp or {}).get("data") or {}).get("relationships") or {}).get("flexible-asset-fields") or {}
            created_fields = created.get("data")
            if created_fields:
                result["fields"] = [{"id": f.get("id")} for f in created_fields]
            return result

        return await run(settings, handler, secrets=_field_secrets(fields))
