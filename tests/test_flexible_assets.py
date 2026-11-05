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


# PRD-21622: organization_id and restricted were added as new optional parameters.


@respx.mock
async def test_update_flexible_asset_can_set_organization_id(call):
    route = respx.patch(f"{BASE}/flexible_assets/789").mock(
        return_value=httpx.Response(200, json={"data": asset(789, **{"organization-id": 42})})
    )
    out = await call("update_flexible_asset", id="789", organization_id=42)
    body = json.loads(route.calls.last.request.content)
    assert body == {"data": {"type": "flexible_assets", "attributes": {"organization-id": 42}}}
    assert out["organization_id"] == 42


@respx.mock
async def test_update_flexible_asset_can_set_restricted_true(call):
    route = respx.patch(f"{BASE}/flexible_assets/789").mock(
        return_value=httpx.Response(200, json={"data": asset(789, restricted=True)})
    )
    out = await call("update_flexible_asset", id="789", restricted=True)
    body = json.loads(route.calls.last.request.content)
    assert body == {"data": {"type": "flexible_assets", "attributes": {"restricted": True}}}
    assert out["restricted"] is True


@respx.mock
async def test_update_flexible_asset_can_set_restricted_false(call):
    route = respx.patch(f"{BASE}/flexible_assets/789").mock(
        return_value=httpx.Response(200, json={"data": asset(789, restricted=False)})
    )
    out = await call("update_flexible_asset", id="789", restricted=False)
    body = json.loads(route.calls.last.request.content)
    # False must not be dropped as if it were "not provided" -- only None means that.
    assert body == {"data": {"type": "flexible_assets", "attributes": {"restricted": False}}}
    assert out["restricted"] is False


@respx.mock
async def test_update_flexible_asset_combines_old_and_new_fields(call):
    route = respx.patch(f"{BASE}/flexible_assets/789").mock(
        return_value=httpx.Response(
            200,
            json={"data": asset(789, traits={"domain-name": "new.example.com"}, **{"organization-id": 42})},
        )
    )
    await call(
        "update_flexible_asset",
        id="789",
        traits={"domain-name": "new.example.com"},
        organization_id=42,
    )
    body = json.loads(route.calls.last.request.content)
    assert body["data"]["attributes"] == {
        "traits": {"domain-name": "new.example.com"},
        "organization-id": 42,
    }


@respx.mock
async def test_get_flexible_asset_type_returns_fields(call):
    # PRD-21624 AC1: fetching an existing type returns its id, name and field definitions.
    included = [
        {
            "id": "1",
            "type": "flexible_asset_fields",
            "attributes": {"name": "Domain Name", "kind": "Text", "required": True, "order": 1},
        },
        {
            "id": "2",
            "type": "flexible_asset_fields",
            "attributes": {"name": "Functional Level", "kind": "Text", "required": False, "order": 2},
        },
    ]
    respx.get(f"{BASE}/flexible_asset_types/456").mock(
        return_value=httpx.Response(200, json={"data": flexible_asset_type(456), "included": included})
    )
    out = await call("get_flexible_asset_type", id="456")
    assert out["id"] == "456"
    assert out["name"] == "BitLocker (Rewst)"
    assert out["fields"] == [
        {"id": "1", "name": "Domain Name", "kind": "Text", "required": True, "order": 1},
        {"id": "2", "name": "Functional Level", "kind": "Text", "required": False, "order": 2},
    ]


@respx.mock
async def test_get_flexible_asset_type_not_found_returns_envelope(call):
    # PRD-21624 AC2: an unknown (or cross-account) type ID returns the standard error envelope.
    respx.get(f"{BASE}/flexible_asset_types/999").mock(
        return_value=httpx.Response(404, json={"errors": [{"title": "not found"}]})
    )
    out = await call("get_flexible_asset_type", id="999")
    assert out["error"]["code"] == "not_found"


@respx.mock
async def test_get_flexible_asset_type_with_no_fields_returns_empty_list(call):
    # PRD-21624 AC3: IT Glue omits `included` entirely when a type has no custom fields configured;
    # the tool must still return `fields: []`, not a missing key and not an error.
    respx.get(f"{BASE}/flexible_asset_types/456").mock(
        return_value=httpx.Response(200, json={"data": flexible_asset_type(456)})
    )
    out = await call("get_flexible_asset_type", id="456")
    assert out["fields"] == []


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


def flexible_asset_field(id_, **attrs):
    base = {"name": "Full Access Record", "kind": "Tag", "order": 860, "tag-type": "Contacts", "show-in-list": False}
    base.update(attrs)
    return {"id": str(id_), "type": "flexible_asset_fields", "attributes": base}


FIELDS_PATH = f"{BASE}/flexible_asset_types/456/relationships/flexible_asset_fields"


@respx.mock
async def test_create_flexible_asset_field_happy_path(call):
    # PRD-21627 AC1: the Rewst flow reads the new field's data.id.
    route = respx.post(FIELDS_PATH).mock(return_value=httpx.Response(201, json={"data": flexible_asset_field(9001)}))
    out = await call(
        "itglue_create_flexible_asset_field",
        flexible_asset_type_id=456,
        name="Full Access Record",
        kind="Tag",
        order=860,
        required=False,
        show_in_list=False,
        use_for_title=False,
        tag_type="Contacts",
        hint="Who has full access",
        default_value="none",
    )
    body = json.loads(route.calls.last.request.content)
    assert body == {
        "data": {
            "type": "flexible_asset_fields",
            "attributes": {
                "name": "Full Access Record",
                "kind": "Tag",
                "order": 860,
                "required": False,
                "show-in-list": False,
                "use-for-title": False,
                "tag-type": "Contacts",
                "hint": "Who has full access",
                "default-value": "none",
            },
        }
    }
    assert out["id"] == "9001"
    assert out["name"] == "Full Access Record"


@respx.mock
async def test_create_flexible_asset_field_omits_unset_optional_fields(call):
    route = respx.post(FIELDS_PATH).mock(return_value=httpx.Response(201, json={"data": flexible_asset_field(9002)}))
    await call("itglue_create_flexible_asset_field", flexible_asset_type_id=456, name="Notes", kind="Textbox")
    body = json.loads(route.calls.last.request.content)
    assert body["data"]["attributes"] == {"name": "Notes", "kind": "Textbox"}


@respx.mock
async def test_create_flexible_asset_field_forwards_kind_and_tag_type(call):
    # Not validated locally: IT Glue is the source of truth for legal kinds and tag types.
    route = respx.post(FIELDS_PATH).mock(return_value=httpx.Response(201, json={"data": flexible_asset_field(9003)}))
    await call(
        "itglue_create_flexible_asset_field",
        flexible_asset_type_id=456,
        name="Full Access Record",
        kind="Tag",
        tag_type="Contacts",
    )
    attrs = json.loads(route.calls.last.request.content)["data"]["attributes"]
    assert attrs["kind"] == "Tag"
    assert attrs["tag-type"] == "Contacts"


async def test_create_flexible_asset_field_rejects_non_numeric_type_id(call):
    with respx.mock(assert_all_called=False) as router:
        route = router.post(url__regex=r".*").mock(return_value=httpx.Response(201))
        out = await call("itglue_create_flexible_asset_field", flexible_asset_type_id="../users", name="X", kind="Text")
    assert out["error"]["code"] == "invalid_argument"
    assert not route.called


@respx.mock
async def test_create_flexible_asset_field_not_found_returns_envelope(call):
    respx.post(f"{BASE}/flexible_asset_types/999/relationships/flexible_asset_fields").mock(
        return_value=httpx.Response(404, json={"errors": [{"title": "not found"}]})
    )
    out = await call("itglue_create_flexible_asset_field", flexible_asset_type_id=999, name="X", kind="Text")
    assert out["error"]["code"] == "not_found"


@respx.mock
async def test_create_flexible_asset_field_error_does_not_leak_default_value(call, caplog):
    respx.post(FIELDS_PATH).mock(side_effect=RuntimeError(f"boom {SECRET_LOOKING_TRAIT}"))
    with caplog.at_level(logging.DEBUG):
        out = await call(
            "itglue_create_flexible_asset_field",
            flexible_asset_type_id=456,
            name="Key",
            kind="Password",
            default_value=SECRET_LOOKING_TRAIT,
        )
    assert out["error"]["code"] == "upstream_error"
    assert SECRET_LOOKING_TRAIT not in json.dumps(out)
    assert SECRET_LOOKING_TRAIT not in caplog.text


async def test_create_flexible_asset_field_annotations(mcp):
    tool = {t.name: t for t in await mcp.list_tools()}["itglue_create_flexible_asset_field"]
    assert tool.annotations.readOnlyHint is False
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is False
    assert set(tool.inputSchema["required"]) == {"flexible_asset_type_id", "name", "kind"}
