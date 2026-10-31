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
async def test_create_flexible_asset_sets_archived_and_restricted(call):
    route = respx.post(f"{BASE}/flexible_assets").mock(
        return_value=httpx.Response(201, json={"data": asset(1002, archived=True, restricted=True)})
    )
    out = await call(
        "create_flexible_asset",
        organization_id=3,
        flexible_asset_type_id=456,
        traits={"domain-name": "corp.example.com"},
        archived=True,
        restricted=True,
    )
    body = json.loads(route.calls.last.request.content)
    assert body["data"]["attributes"]["archived"] is True
    assert body["data"]["attributes"]["restricted"] is True
    assert out["archived"] is True
    assert out["restricted"] is True


@respx.mock
async def test_create_flexible_asset_forwards_html_trait_value_unmodified(call):
    html_value = "<table><tr><td>key</td><td>value</td></tr></table>"
    route = respx.post(f"{BASE}/flexible_assets").mock(
        return_value=httpx.Response(201, json={"data": asset(1003, traits={"rewst-org-variables": html_value})})
    )
    out = await call(
        "create_flexible_asset",
        organization_id=3,
        flexible_asset_type_id=456,
        traits={"rewst-org-variables": html_value},
    )
    body = json.loads(route.calls.last.request.content)
    assert body["data"]["attributes"]["traits"] == {"rewst-org-variables": html_value}
    assert out["traits"] == {"rewst-org-variables": html_value}


@respx.mock
async def test_create_flexible_asset_error_does_not_leak_trait_values(call, caplog):
    respx.post(f"{BASE}/flexible_assets").mock(side_effect=RuntimeError(f"boom {SECRET_LOOKING_TRAIT}"))
    with caplog.at_level(logging.DEBUG):
        out = await call(
            "create_flexible_asset",
            organization_id=3,
            flexible_asset_type_id=456,
            traits={"api-key": SECRET_LOOKING_TRAIT},
            archived=True,
            restricted=True,
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


def flexible_asset_type(id_, relationships=None, **attrs):
    base = {"name": "BitLocker (Rewst)", "enabled": True, "description": None, "icon": None}
    base.update(attrs)
    data = {"id": str(id_), "type": "flexible_asset_types", "attributes": base}
    if relationships is not None:
        data["relationships"] = relationships
    return data


@respx.mock
async def test_create_flexible_asset_type_name_only(call):
    route = respx.post(f"{BASE}/flexible_asset_types").mock(
        return_value=httpx.Response(201, json={"data": flexible_asset_type(1, name="BitLocker (Rewst)")})
    )
    out = await call("itglue_create_flexible_asset_type", name="BitLocker (Rewst)")
    body = json.loads(route.calls.last.request.content)
    assert body == {"data": {"type": "flexible_asset_types", "attributes": {"name": "BitLocker (Rewst)"}}}
    assert out["id"] == "1"
    assert out["name"] == "BitLocker (Rewst)"


@respx.mock
async def test_create_flexible_asset_type_forwards_all_attributes(call):
    route = respx.post(f"{BASE}/flexible_asset_types").mock(
        return_value=httpx.Response(201, json={"data": flexible_asset_type(2)})
    )
    await call(
        "itglue_create_flexible_asset_type",
        name="BitLocker (Rewst)",
        enabled=True,
        description="Store BitLocker keys here",
        icon="lock",
    )
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "data": {
            "type": "flexible_asset_types",
            "attributes": {
                "name": "BitLocker (Rewst)",
                "enabled": True,
                "description": "Store BitLocker keys here",
                "icon": "lock",
            },
        }
    }


@respx.mock
async def test_create_flexible_asset_type_omits_unset_optional_attributes(call):
    route = respx.post(f"{BASE}/flexible_asset_types").mock(
        return_value=httpx.Response(201, json={"data": flexible_asset_type(3)})
    )
    await call("itglue_create_flexible_asset_type", name="BitLocker (Rewst)", enabled=True)
    body = json.loads(route.calls.last.request.content)
    assert body["data"]["attributes"] == {"name": "BitLocker (Rewst)", "enabled": True}
    assert "description" not in body["data"]["attributes"]
    assert "icon" not in body["data"]["attributes"]


@respx.mock
async def test_create_flexible_asset_type_sends_fields_relationship(call):
    route = respx.post(f"{BASE}/flexible_asset_types").mock(
        return_value=httpx.Response(
            201,
            json={
                "data": flexible_asset_type(
                    4,
                    relationships={"flexible-asset-fields": {"data": [{"id": "456", "type": "flexible_asset_fields"}]}},
                )
            },
        )
    )
    out = await call(
        "itglue_create_flexible_asset_type",
        name="BitLocker (Rewst)",
        fields=[{"name": "BitLocker Keys", "kind": "Textbox", "order": 0, "show_in_list": True}],
    )
    body = json.loads(route.calls.last.request.content)
    assert body["data"]["relationships"] == {
        "flexible-asset-fields": {
            "data": [
                {
                    "type": "flexible_asset_fields",
                    "attributes": {"name": "BitLocker Keys", "kind": "Textbox", "order": 0, "show-in-list": True},
                }
            ]
        }
    }
    assert out["fields"] == [{"id": "456"}]


@respx.mock
async def test_create_flexible_asset_type_without_fields_omits_relationships(call):
    route = respx.post(f"{BASE}/flexible_asset_types").mock(
        return_value=httpx.Response(201, json={"data": flexible_asset_type(5)})
    )
    await call("itglue_create_flexible_asset_type", name="BitLocker (Rewst)")
    body = json.loads(route.calls.last.request.content)
    assert "relationships" not in body["data"]


@respx.mock
async def test_create_flexible_asset_type_with_empty_fields_list_omits_relationships(call):
    route = respx.post(f"{BASE}/flexible_asset_types").mock(
        return_value=httpx.Response(201, json={"data": flexible_asset_type(6)})
    )
    await call("itglue_create_flexible_asset_type", name="BitLocker (Rewst)", fields=[])
    body = json.loads(route.calls.last.request.content)
    assert "relationships" not in body["data"]


async def test_create_flexible_asset_type_rejects_field_missing_kind(call):
    out = await call("itglue_create_flexible_asset_type", name="BitLocker (Rewst)", fields=[{"name": "BitLocker Keys"}])
    assert out["error"]["code"] == "invalid_argument"
    assert "fields[0]" in out["error"]["message"]


async def test_create_flexible_asset_type_rejects_field_missing_name(call):
    out = await call("itglue_create_flexible_asset_type", name="BitLocker (Rewst)", fields=[{"kind": "Textbox"}])
    assert out["error"]["code"] == "invalid_argument"
    assert "fields[0]" in out["error"]["message"]


@respx.mock
async def test_create_flexible_asset_type_duplicate_name_maps_to_invalid_argument(call):
    respx.post(f"{BASE}/flexible_asset_types").mock(
        return_value=httpx.Response(409, json={"errors": [{"title": "Name has already been taken"}]})
    )
    out = await call("itglue_create_flexible_asset_type", name="BitLocker (Rewst)")
    assert out["error"]["code"] == "invalid_argument"


@respx.mock
async def test_create_flexible_asset_type_error_does_not_leak_default_value(call, caplog):
    respx.post(f"{BASE}/flexible_asset_types").mock(side_effect=RuntimeError(f"boom {SECRET_LOOKING_TRAIT}"))
    with caplog.at_level(logging.DEBUG):
        out = await call(
            "itglue_create_flexible_asset_type",
            name="BitLocker (Rewst)",
            fields=[{"name": "Key", "kind": "Password", "default_value": SECRET_LOOKING_TRAIT}],
        )
    assert out["error"]["code"] == "upstream_error"
    assert SECRET_LOOKING_TRAIT not in json.dumps(out)
    assert SECRET_LOOKING_TRAIT not in caplog.text
