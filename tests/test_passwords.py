# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Password rotation: find an entry with search_passwords, change it with update_password (PRD-21374)."""

import json
import logging

import httpx
import pytest
import respx

from conftest import BASE

pytestmark = pytest.mark.usefixtures("creds")

SECRET = "N3w-Rotated-Secret!"


def entry(id_, name, username, **extra):
    attrs = {
        "organization-id": 3,
        "name": name,
        "username": username,
        "password-category-name": "Cloud",
        "password-category-id": 15,
        "updated-at": "2026-10-01T10:00:00.000Z",
        **extra,
    }
    return {"id": str(id_), "type": "passwords", "attributes": attrs}


@respx.mock
async def test_search_passwords_maps_fields_and_strips_secrets(call):
    route = respx.get(f"{BASE}/passwords").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    entry(5, "M365 Admin", "admin@example.com", password="plain-1", **{"otp-secret": "otp"}),
                    entry(6, "VPN", "vpn-user"),
                ],
                "meta": {"current-page": 1, "total-count": 2, "total-pages": 1},
            },
        )
    )
    out = await call("search_passwords", organization_id=3, name="M365")
    params = route.calls.last.request.url.params
    assert params["filter[organization_id]"] == "3"
    assert params["filter[name]"] == "M365"
    first = out["items"][0]
    assert first["id"] == "5"
    assert first["name"] == "M365 Admin"
    assert first["username"] == "admin@example.com"
    assert first["password_category_name"] == "Cloud"
    assert first["updated_at"] == "2026-10-01T10:00:00.000Z"
    assert "password" not in first and "otp_secret" not in first
    assert "plain-1" not in json.dumps(out)
    assert out["has_more"] is False


@respx.mock
async def test_search_passwords_username_filter_is_local_and_pages_continue(call):
    route = respx.get(f"{BASE}/passwords").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [entry(1, "A", "bob"), entry(2, "B", "Jane.Doe"), entry(3, "C", None)],
                "meta": {"current-page": 1, "next-page": 2, "total-count": 5},
            },
        )
    )
    out = await call("search_passwords", organization_id=3, username="jane", page_size=3)
    params = route.calls.last.request.url.params
    assert "filter[username]" not in params  # not an IT Glue filter
    assert params["page[size]"] == "3" and params["page[number]"] == "1"
    assert [i["id"] for i in out["items"]] == ["2"]
    assert out["count"] == 1
    assert out["has_more"] is True
    assert out["next_offset"] == 3


@respx.mock
async def test_search_passwords_offset_requests_the_right_page(call):
    route = respx.get(f"{BASE}/passwords").mock(
        return_value=httpx.Response(200, json={"data": [entry(51, "X", "x")], "meta": {"total-count": 51}})
    )
    out = await call("search_passwords", organization_id=3, page_size=50, offset=50)
    params = route.calls.last.request.url.params
    assert params["page[number]"] == "2"
    assert [i["id"] for i in out["items"]] == ["51"]
    assert out["has_more"] is False


@respx.mock
async def test_update_password_sends_only_supplied_fields(call):
    route = respx.patch(f"{BASE}/passwords/5").mock(
        return_value=httpx.Response(200, json={"data": entry(5, "M365 Admin", "admin@example.com", password=SECRET)})
    )
    out = await call("update_password", id="5", password=SECRET, notes="Rotated")
    request = route.calls.last.request
    assert json.loads(request.content) == {
        "data": {"type": "passwords", "attributes": {"password": SECRET, "notes": "Rotated"}}
    }
    assert request.url.params["show_password"] == "false"
    assert out["id"] == "5" and out["name"] == "M365 Admin"
    assert "password" not in out
    assert SECRET not in json.dumps(out)


@respx.mock
async def test_update_password_with_organization_uses_nested_route(call):
    route = respx.patch(f"{BASE}/organizations/3/relationships/passwords/5").mock(
        return_value=httpx.Response(200, json={"data": entry(5, "M365 Admin", "admin@example.com")})
    )
    await call("update_password", organization_id=3, id="5", password=SECRET)
    assert json.loads(route.calls.last.request.content) == {
        "data": {"type": "passwords", "attributes": {"password": SECRET}}
    }


@respx.mock
async def test_update_password_keeps_empty_string_as_supplied(call):
    route = respx.patch(f"{BASE}/passwords/5").mock(return_value=httpx.Response(200, json={"data": entry(5, "A", "a")}))
    await call("update_password", id="5", notes="")
    assert json.loads(route.calls.last.request.content)["data"]["attributes"] == {"notes": ""}


async def test_update_password_without_fields_is_rejected(call):
    out = await call("update_password", id="5")
    assert out["error"]["code"] == "invalid_argument"


@respx.mock
async def test_update_password_redacts_secret_in_errors_and_logs(call, caplog):
    respx.patch(f"{BASE}/passwords/5").mock(
        return_value=httpx.Response(422, json={"errors": [{"detail": f"Password {SECRET} was used before"}]})
    )
    with caplog.at_level(logging.DEBUG):
        out = await call("update_password", id="5", password=SECRET)
    assert out["error"]["code"] == "invalid_argument"
    assert SECRET not in out["error"]["message"]
    assert "[redacted]" in out["error"]["message"]
    assert SECRET not in caplog.text


@respx.mock
async def test_update_password_unexpected_error_logs_no_secret(call, caplog):
    respx.patch(f"{BASE}/passwords/5").mock(side_effect=RuntimeError(f"boom {SECRET}"))
    with caplog.at_level(logging.DEBUG):
        out = await call("update_password", id="5", password=SECRET)
    assert out["error"]["code"] == "upstream_error"
    assert "RuntimeError" in caplog.text
    assert SECRET not in caplog.text


@respx.mock
async def test_create_password_redacts_secret_in_logs(call, caplog):
    respx.post(f"{BASE}/organizations/3/relationships/passwords").mock(side_effect=RuntimeError(SECRET))
    with caplog.at_level(logging.DEBUG):
        out = await call("create_password", organization_id=3, name="M365", password=SECRET)
    assert out["error"]["code"] == "upstream_error"
    assert SECRET not in caplog.text


async def test_password_params_are_marked_secret(mcp):
    tools = {t.name: t for t in await mcp.list_tools()}
    for name in ("create_password", "update_password"):
        prop = tools[name].inputSchema["properties"]["password"]
        assert prop["writeOnly"] is True and prop["format"] == "password", name
    assert tools["update_password"].inputSchema["required"] == ["id"]
