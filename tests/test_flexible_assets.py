# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""get/create/update_flexible_asset: single-record management of custom records (PRD-21217)."""

import json
import logging

import httpx
import pytest
import respx
from conftest import BASE

pytestmark = pytest.mark.usefixtures("creds")

SECRET_LOOKING_TRAIT = "sk-live-looks-like-a-credential"


def asset(id_, **attrs):
    base = {
        "organization-id": 3,
        "flexible-asset-type-id": 456,
        "name": "Primary AD Domain",
        "traits": {"domain-name": "corp.example.com"},
        "archived": False,
    }
    base.update(attrs)
    return {"id": str(id_), "type": "flexible_assets", "attributes": base}


@respx.mock
async def test_get_flexible_asset_returns_full_record(call):
    respx.get(f"{BASE}/flexible_assets/789").mock(return_value=httpx.Response(200, json={"data": asset(789)}))
    out = await call("get_flexible_asset", id="789")
    assert out["id"] == "789"
    assert out["name"] == "Primary AD Domain"
    assert out["organization_id"] == 3
    assert out["flexible_asset_type_id"] == 456
    assert out["traits"] == {"domain-name": "corp.example.com"}
    assert out["archived"] is False


@respx.mock
async def test_get_flexible_asset_not_found_returns_envelope(call):
    respx.get(f"{BASE}/flexible_assets/999").mock(
        return_value=httpx.Response(404, json={"errors": [{"title": "not found"}]})
    )
    out = await call("get_flexible_asset", id="999")
    assert out["error"]["code"] == "not_found"


@respx.mock
async def test_create_flexible_asset_happy_path(call):
    route = respx.post(f"{BASE}/flexible_assets").mock(return_value=httpx.Response(201, json={"data": asset(1001)}))
    out = await call(
        "create_flexible_asset",
        organization_id=3,
        flexible_asset_type_id=456,
        name="Primary AD Domain",
        traits={"domain-name": "corp.example.com"},
    )
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "data": {
            "type": "flexible_assets",
            "attributes": {
                "organization-id": 3,
                "flexible-asset-type-id": 456,
                "name": "Primary AD Domain",
                "traits": {"domain-name": "corp.example.com"},
            },
        }
    }
    assert out["id"] == "1001"
    assert out["name"] == "Primary AD Domain"
    assert out["traits"] == {"domain-name": "corp.example.com"}


@respx.mock
async def test_create_flexible_asset_error_does_not_leak_trait_values(call, caplog):
    respx.post(f"{BASE}/flexible_assets").mock(side_effect=RuntimeError(f"boom {SECRET_LOOKING_TRAIT}"))
    with caplog.at_level(logging.DEBUG):
        out = await call(
            "create_flexible_asset",
            organization_id=3,
            flexible_asset_type_id=456,
            traits={"api-key": SECRET_LOOKING_TRAIT},
        )
    assert out["error"]["code"] == "upstream_error"
    assert SECRET_LOOKING_TRAIT not in json.dumps(out)
    assert SECRET_LOOKING_TRAIT not in caplog.text


@respx.mock
async def test_update_flexible_asset_sends_only_changed_fields(call):
    route = respx.patch(f"{BASE}/flexible_assets/789").mock(
        return_value=httpx.Response(200, json={"data": asset(789, name="Renamed")})
    )
    out = await call("update_flexible_asset", id="789", name="Renamed")
    body = json.loads(route.calls.last.request.content)
    assert body == {"data": {"type": "flexible_assets", "attributes": {"name": "Renamed"}}}
    assert "traits" not in body["data"]["attributes"]
    assert out["name"] == "Renamed"


@respx.mock
async def test_update_flexible_asset_can_set_archived_alongside_other_fields(call):
    route = respx.patch(f"{BASE}/flexible_assets/789").mock(
        return_value=httpx.Response(200, json={"data": asset(789, archived=True)})
    )
    await call("update_flexible_asset", id="789", archived=True)
    body = json.loads(route.calls.last.request.content)
    assert body["data"]["attributes"] == {"archived": True}
    assert route.calls.last.request is not None


async def test_update_flexible_asset_rejects_empty_call(call):
    out = await call("update_flexible_asset", id="789")
    assert out["error"]["code"] == "invalid_argument"


@respx.mock
async def test_update_flexible_asset_not_found_returns_envelope(call):
    respx.patch(f"{BASE}/flexible_assets/999").mock(
        return_value=httpx.Response(404, json={"errors": [{"title": "not found"}]})
    )
    out = await call("update_flexible_asset", id="999", name="x")
    assert out["error"]["code"] == "not_found"
