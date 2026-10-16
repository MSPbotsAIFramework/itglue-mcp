# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Process-level settings. Tenant credentials are never read from here."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

API_KEY_HEADER = "X-ITGlue-API-Key"
REGION_HEADER = "X-ITGlue-Region"
BASE_URL_HEADER = "X-ITGlue-Base-URL"

REGION_BASE_URLS = {
    "us": "https://api.itglue.com",
    "eu": "https://api.eu.itglue.com",
    "au": "https://api.au.itglue.com",
}
DEFAULT_REGION = "us"

# A custom base URL must be HTTPS and point at an IT Glue host, so a tenant
# cannot make the server send its API key (or reach) anywhere else.
ALLOWED_BASE_URL_SUFFIX = ".itglue.com"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    mcp_transport: Literal["stdio", "http"] = "http"
    mcp_http_host: str = "0.0.0.0"
    mcp_http_port: int = 8080

    # Outbound HTTP behaviour.
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    max_retries: int = 3
    # Upper bound for one tool call including retries (must stay below 120s).
    call_budget_seconds: float = 100.0


def get_settings() -> Settings:
    return Settings()
