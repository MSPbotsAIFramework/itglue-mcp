# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Locations: an organization's sites with address and phone."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .. import api
from ..config import Settings
from ._common import CREATE, READ, UPDATE, PageNumber, PageSize, ToolInputError, paging, run, seg

Name = Annotated[str | None, Field(description="Location name.")]
CountryId = Annotated[int | None, Field(description="IT Glue country ID (usually required when creating).")]
RegionId = Annotated[int | None, Field(description="IT Glue region (state/province) ID.")]
Address1 = Annotated[str | None, Field(description="Address line 1.")]
Address2 = Annotated[str | None, Field(description="Address line 2.")]
City = Annotated[str | None, Field(description="City.")]
PostalCode = Annotated[str | None, Field(description="Postal or ZIP code.")]
Phone = Annotated[str | None, Field(description="Phone number.")]
Fax = Annotated[str | None, Field(description="Fax number.")]
Notes = Annotated[str | None, Field(description="Notes.")]
Primary = Annotated[bool | None, Field(description="Mark as the organization's primary location.")]


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="search_locations",
        description=(
            "Find an organization's locations (sites) with their address and phone number. "
            "Use this, not flexible assets, to look up a client's address or main phone."
        ),
        annotations=READ,
        structured_output=False,
    )
    async def search_locations(
        organization_id: Annotated[
            int | None, Field(description="Organization ID (recommended; locations belong to organizations).")
        ] = None,
        name: Annotated[str | None, Field(description="Location name to match.")] = None,
        city: Annotated[str | None, Field(description="City.")] = None,
        region_id: RegionId = None,
        country_id: Annotated[int | None, Field(description="IT Glue country ID.")] = None,
        psa_id: Annotated[str | None, Field(description="ID of the location in the linked PSA.")] = None,
        page_size: PageSize = None,
        page_number: PageNumber = None,
        sort: Annotated[
            str | None,
            Field(description="Sort field: name, id, primary, created_at or updated_at. Prefix '-' for descending."),
        ] = None,
    ) -> str:
        size, number, params = paging(page_size, page_number)
        params.update(
            {
                "filter[name]": name,
                "filter[city]": city,
                "filter[region_id]": region_id,
                "filter[country_id]": country_id,
                "filter[psa_id]": psa_id,
                "sort": sort,
            }
        )

        async def handler(client: api.ITGlueClient):
            if organization_id is not None:
                path = f"/organizations/{seg(organization_id)}/relationships/locations"
            else:
                path = "/locations"
            return api.page(await client.get(path, params), number, size)

        return await run(settings, handler)

    @mcp.tool(
        name="get_location",
        description="Get one IT Glue location by ID, including its full address and phone number.",
        annotations=READ,
        structured_output=False,
    )
    async def get_location(id: Annotated[str, Field(description="Location ID.")]) -> str:
        async def handler(client: api.ITGlueClient):
            return api.item(await client.get(f"/locations/{seg(id)}"))

        return await run(settings, handler)

    @mcp.tool(
        name="create_location",
        description=(
            "Create a location (site) for an IT Glue organization. A name is required and IT Glue "
            "usually also needs country_id."
        ),
        annotations=CREATE,
        structured_output=False,
    )
    async def create_location(
        organization_id: Annotated[int, Field(description="Organization that owns the location.")],
        name: Annotated[str, Field(description="Location name.")],
        country_id: CountryId = None,
        region_id: RegionId = None,
        address_1: Address1 = None,
        address_2: Address2 = None,
        city: City = None,
        postal_code: PostalCode = None,
        phone: Phone = None,
        fax: Fax = None,
        notes: Notes = None,
        primary: Primary = None,
    ) -> str:
        values = dict(
            name=name,
            country_id=country_id,
            region_id=region_id,
            address_1=address_1,
            address_2=address_2,
            city=city,
            postal_code=postal_code,
            phone=phone,
            fax=fax,
            notes=notes,
            primary=primary,
        )

        async def handler(client: api.ITGlueClient):
            path = f"/organizations/{seg(organization_id)}/relationships/locations"
            return api.item(await client.post(path, api.attributes("locations", values)))

        return await run(settings, handler)

    @mcp.tool(
        name="update_location",
        description="Update an IT Glue location. Only the fields you pass are changed.",
        annotations=UPDATE,
        structured_output=False,
    )
    async def update_location(
        organization_id: Annotated[int, Field(description="Organization that owns the location.")],
        id: Annotated[str, Field(description="Location ID.")],
        name: Name = None,
        country_id: CountryId = None,
        region_id: RegionId = None,
        address_1: Address1 = None,
        address_2: Address2 = None,
        city: City = None,
        postal_code: PostalCode = None,
        phone: Phone = None,
        fax: Fax = None,
        notes: Notes = None,
        primary: Primary = None,
    ) -> str:
        values = dict(
            name=name,
            country_id=country_id,
            region_id=region_id,
            address_1=address_1,
            address_2=address_2,
            city=city,
            postal_code=postal_code,
            phone=phone,
            fax=fax,
            notes=notes,
            primary=primary,
        )

        async def handler(client: api.ITGlueClient):
            if not any(v is not None for v in values.values()):
                raise ToolInputError("Pass at least one field to change.")
            path = f"/organizations/{seg(organization_id)}/relationships/locations/{seg(id)}"
            return api.item(await client.patch(path, api.attributes("locations", values)))

        return await run(settings, handler)
