# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""FastMCP server and HTTP app."""

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .config import Settings
from .credentials import CredentialMiddleware
from .tools import (
    attachments,
    configurations,
    documents,
    flexible_assets,
    locations,
    organizations,
    passwords,
    user_metrics,
)

INSTRUCTIONS = (
    "IT Glue is the IT documentation platform MSPs use to record everything about their clients: "
    "organizations (clients), configurations (devices and assets), locations (sites), passwords, "
    "documents and flexible assets (custom record types such as Active Directory or Wireless). "
    "Almost everything belongs to an organization, so start with search_organizations to get the "
    "organization ID. Typical flows: devices -> search_configurations; client address or phone -> "
    "search_locations; credentials -> search_passwords then get_password; knowledge articles -> "
    "search_documents then get_document; custom records -> list_flexible_asset_types then "
    "search_flexible_assets. To edit a document body: list_document_sections, then "
    "create/update/delete_document_section, then publish_document. Prefer archive over delete. "
    "Ask the user before archiving, unarchiving or deleting anything."
)


def create_mcp(settings: Settings) -> FastMCP:
    mcp = FastMCP(
        name="itglue-mcp",
        instructions=INSTRUCTIONS,
        stateless_http=True,
        json_response=True,
        # The gateway forwards requests with its own Host header; DNS-rebinding
        # protection would reject them with 421.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    for module in (
        organizations,
        configurations,
        locations,
        passwords,
        documents,
        attachments,
        flexible_assets,
        user_metrics,
    ):
        module.register(mcp, settings)
    return mcp


def create_app(settings: Settings) -> Starlette:
    mcp = create_mcp(settings)
    mcp_app = mcp.streamable_http_app()

    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    # Mount() does not run a sub-app's lifespan; without forwarding it the
    # session manager never starts and /mcp fails while /health still passes.
    return Starlette(
        routes=[Route("/health", health), Mount("/", app=CredentialMiddleware(mcp_app))],
        lifespan=lambda app: mcp_app.router.lifespan_context(app),
    )
