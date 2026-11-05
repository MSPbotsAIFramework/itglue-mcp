# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
import pytest
from starlette.testclient import TestClient

from itglue_mcp import credentials
from itglue_mcp.config import Settings
from itglue_mcp.server import create_app

LIST = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture
def client():
    with TestClient(create_app(Settings())) as c:
        yield c


def test_health_needs_no_credentials(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_missing_api_key_is_401(client):
    r = client.post("/mcp", json=LIST, headers=HEADERS)
    assert r.status_code == 401
    assert "X-ITGlue-API-Key" in r.json()["required_headers"]


INIT = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "probe", "version": "1"}},
}


# PRD-20835: the admin console refreshes the tool catalog with a placeholder in every header.
@pytest.mark.parametrize(
    "extra",
    [
        {"X-ITGlue-Region": "placeholder"},
        {"X-ITGlue-Base-URL": "placeholder"},
        {"X-ITGlue-Base-URL": "https://evil.example.com"},
        {"X-ITGlue-Region": "placeholder", "X-ITGlue-Base-URL": "placeholder"},
    ],
)
def test_malformed_region_or_base_url_does_not_block_initialize_or_tools_list(client, extra):
    h = {**HEADERS, "X-ITGlue-API-Key": "placeholder", **extra}
    assert client.post("/mcp", json=INIT, headers=h).status_code == 200
    r = client.post("/mcp", json=LIST, headers=h)
    assert r.status_code == 200
    assert len(r.json()["result"]["tools"]) == 38


@pytest.mark.parametrize("key", ["", "   "])
def test_empty_api_key_is_still_401(client, key):
    h = {**HEADERS, "X-ITGlue-API-Key": key, "X-ITGlue-Region": "placeholder"}
    assert client.post("/mcp", json=LIST, headers=h).status_code == 401


def test_tools_list_is_stateless(client):
    # No initialize / session id: must still answer 200.
    h = {**HEADERS, "x-itglue-api-key": "k"}
    r = client.post("/mcp", json=LIST, headers=h)
    assert r.status_code == 200
    assert len(r.json()["result"]["tools"]) == 38


@pytest.mark.parametrize(
    ("region", "base", "expected"),
    [
        (None, None, "https://api.itglue.com"),
        ("EU", None, "https://api.eu.itglue.com"),
        ("au", None, "https://api.au.itglue.com"),
        ("us", "https://api.eu.itglue.com/", "https://api.eu.itglue.com"),
        (None, "https://itglue.com", "https://itglue.com"),
    ],
)
def test_resolve_base_url(region, base, expected):
    assert credentials.resolve_base_url(region, base) == expected


@pytest.mark.parametrize(
    ("region", "base"),
    [("mars", None), (None, "http://api.itglue.com"), (None, "https://api.itglue.com.evil.io"), (None, "https://x.y")],
)
def test_resolve_base_url_rejects(region, base):
    with pytest.raises(credentials.CredentialError):
        credentials.resolve_base_url(region, base)


def test_credentials_do_not_leak_between_requests():
    assert credentials.current() is None
