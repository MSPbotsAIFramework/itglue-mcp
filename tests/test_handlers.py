# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Tool behaviour against a mocked IT Glue API."""

import json

import httpx
import pytest
import respx

from conftest import BASE

pytestmark = pytest.mark.usefixtures("creds")


def doc(type_, id_, **attrs):
    return {"id": str(id_), "type": type_, "attributes": attrs}


@respx.mock
async def test_search_organizations_paging_and_filters(call):
    route = respx.get(f"{BASE}/organizations").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [doc("organizations", 1, **{"name": "Acme", "organization-type-name": "Client"})],
                "meta": {"current-page": 1, "next-page": 2, "total-count": 120},
            },
        )
    )
    out = await call("search_organizations", name="Acme", page_size=500)
    params = route.calls.last.request.url.params
    assert params["filter[name]"] == "Acme"
    assert params["page[size]"] == "200"  # capped
    assert route.calls.last.request.headers["x-api-key"] == "test-key"
    assert out["items"] == [{"id": "1", "name": "Acme", "organization_type_name": "Client"}]
    assert out["has_more"] is True and out["total_count"] == 120


@respx.mock
async def test_missing_credentials_envelope(call):
    from itglue_mcp import credentials

    token = credentials._current.set(None)
    try:
        out = await call("get_organization", id="1")
    finally:
        credentials._current.reset(token)
    assert out["error"]["code"] == "not_configured"


@respx.mock
@pytest.mark.parametrize(
    ("status", "code", "retryable"),
    [(401, "unauthorized", False), (403, "unauthorized", False), (404, "not_found", False),
     (422, "invalid_argument", False), (500, "upstream_error", True)],
)
async def test_error_mapping(call, status, code, retryable):
    respx.get(f"{BASE}/organizations/9").mock(
        return_value=httpx.Response(status, json={"errors": [{"title": "nope"}]})
    )
    out = await call("get_organization", id="9")
    assert out["error"]["code"] == code
    assert out["error"]["retryable"] is retryable


@respx.mock
async def test_retries_rate_limit_then_succeeds(call):
    route = respx.get(f"{BASE}/organization_types").mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200, json={"data": []})]
    )
    out = await call("itglue_health_check")
    assert out["status"] == "ok" and route.call_count == 2


@pytest.mark.parametrize(
    "message",
    [
        "X-ITGlue-Region must be one of: us, eu, au.",
        "X-ITGlue-Base-URL must be an https URL on an IT Glue host (*.itglue.com).",
    ],
)
@respx.mock
async def test_malformed_region_or_base_url_is_invalid_argument_without_calling_api(call, message):
    # PRD-20835: the header is checked when a tool runs; nothing is sent to an unchecked host.
    from itglue_mcp import credentials

    bad = credentials.Credentials(api_key="test-key", base_url="", header_error=message)
    token = credentials._current.set(bad)
    try:
        out = await call("get_organization", id="1")
    finally:
        credentials._current.reset(token)
    assert out["error"]["code"] == "invalid_argument" and out["error"]["message"] == message
    assert respx.calls.call_count == 0


async def test_non_numeric_id_is_rejected_without_calling_api(call):
    out = await call("get_organization", id="1/../../users")
    assert out["error"]["code"] == "invalid_argument"


@respx.mock
async def test_search_passwords_never_returns_secrets(call):
    respx.get(f"{BASE}/passwords").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    doc("passwords", 5, name="M365", username="jane@example.com", password="s3cret"),
                    doc("passwords", 6, name="VPN", username="bob@example.com", password="x"),
                ]
            },
        )
    )
    out = await call("search_passwords", organization_id=3, username="JANE")
    assert [i["id"] for i in out["items"]] == ["5"]
    assert "password" not in out["items"][0]


@respx.mock
async def test_get_password_shows_secret_by_default(call):
    route = respx.get(f"{BASE}/passwords/5").mock(
        return_value=httpx.Response(200, json={"data": doc("passwords", 5, password="s3cret")})
    )
    out = await call("get_password", id="5")
    assert route.calls.last.request.url.params["show_password"] == "true"
    assert out["password"] == "s3cret"


@respx.mock
async def test_create_password_does_not_echo_secret(call):
    route = respx.post(f"{BASE}/organizations/3/relationships/passwords").mock(
        return_value=httpx.Response(201, json={"data": doc("passwords", 7, name="M365", password="s3cret")})
    )
    out = await call("create_password", organization_id=3, name="M365", password="s3cret", username="jane")
    sent = json.loads(route.calls.last.request.content)
    assert sent["data"]["type"] == "passwords"
    assert sent["data"]["attributes"]["password"] == "s3cret"
    assert route.calls.last.request.headers["content-type"] == "application/vnd.api+json"
    assert out == {"id": "7", "name": "M365"}


@respx.mock
async def test_create_location_uses_dasherized_attributes(call):
    route = respx.post(f"{BASE}/organizations/3/relationships/locations").mock(
        return_value=httpx.Response(201, json={"data": doc("locations", 8, name="HQ")})
    )
    await call("create_location", organization_id=3, name="HQ", country_id=1, postal_code="12345")
    attrs = json.loads(route.calls.last.request.content)["data"]["attributes"]
    assert attrs == {"name": "HQ", "country-id": 1, "postal-code": "12345"}


@respx.mock
async def test_update_location_requires_a_field(call):
    out = await call("update_location", organization_id=3, id="8")
    assert out["error"]["code"] == "invalid_argument"


@respx.mock
async def test_create_document_with_content_adds_section_and_publishes(call):
    respx.post(f"{BASE}/organizations/3/relationships/documents").mock(
        return_value=httpx.Response(201, json={"data": doc("documents", 40, name="Runbook")})
    )
    section = respx.post(f"{BASE}/documents/40/relationships/sections").mock(
        return_value=httpx.Response(
            201, json={"data": doc("document-sections", 1, **{"resource-type": "Document::Text", "content": "<p>x</p>"})}
        )
    )
    publish = respx.patch(f"{BASE}/documents/40/publish").mock(
        return_value=httpx.Response(200, json={"data": doc("documents", 40)})
    )
    out = await call("create_document", organization_id=3, name="Runbook", content="<p>x</p>")
    assert json.loads(section.calls.last.request.content)["data"]["attributes"]["resource-type"] == "Document::Text"
    assert publish.called and out["published"] is True and out["document"]["id"] == "40"


@respx.mock
async def test_heading_section_gets_level(call):
    route = respx.post(f"{BASE}/documents/40/relationships/sections").mock(
        return_value=httpx.Response(201, json={"data": doc("document-sections", 2)})
    )
    await call("create_document_section", document_id=40, section_type="heading", content="Intro")
    attrs = json.loads(route.calls.last.request.content)["data"]["attributes"]
    assert attrs == {"resource-type": "Document::Heading", "content": "Intro", "level": 2}


@respx.mock
async def test_delete_document_sends_bulk_body(call):
    route = respx.delete(f"{BASE}/documents").mock(return_value=httpx.Response(200, json={"data": []}))
    out = await call("delete_document", document_id="40")
    assert json.loads(route.calls.last.request.content) == {
        "data": [{"type": "documents", "attributes": {"id": 40}}]
    }
    assert out["deleted"] is True


@respx.mock
async def test_search_documents_defaults_to_all_folders(call):
    route = respx.get(f"{BASE}/organizations/3/relationships/documents").mock(
        return_value=httpx.Response(200, json={"data": [doc("documents", 1, name="VPN Guide")]})
    )
    out = await call("search_documents", organization_id=3, name="vpn")
    assert route.calls.last.request.url.params["filter[document_folder_id]"] == "null"
    assert out["count"] == 1


@respx.mock
async def test_get_document_returns_sections(call):
    respx.get(f"{BASE}/organizations/3/relationships/documents/40").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": doc(
                    "documents",
                    40,
                    name="Runbook",
                    content="---\n- id: 1",
                    sections=[{"id": 1, "resource-type": "Document::Heading", "content": "Intro", "level": 1}],
                )
            },
        )
    )
    out = await call("get_document", organization_id=3, id="40")
    assert out["document"] == {"id": "40", "name": "Runbook"}
    assert out["items"][0]["resource_type"] == "Document::Heading"


@respx.mock
async def test_archive_configuration(call):
    route = respx.patch(f"{BASE}/configurations/11").mock(
        return_value=httpx.Response(200, json={"data": doc("configurations", 11, name="FW01", archived=True)})
    )
    out = await call("archive_configuration", configuration_id=11)
    assert json.loads(route.calls.last.request.content)["data"]["attributes"] == {"archived": True}
    assert out["archived"] is True


@respx.mock
async def test_create_attachment_validates_base64(call):
    out = await call("create_attachment", resource_type="documents", resource_id=40, file_name="a.png", content="%%%")
    assert out["error"]["code"] == "invalid_argument"


@respx.mock
async def test_create_attachment_strips_data_prefix(call):
    route = respx.post(f"{BASE}/documents/40/relationships/attachments").mock(
        return_value=httpx.Response(201, json={"data": doc("attachments", 3, **{"download-url": "https://x/3"})})
    )
    out = await call(
        "create_attachment", resource_type="documents", resource_id=40, file_name="a.png",
        content="data:image/png;base64,aGVsbG8=",
    )
    sent = json.loads(route.calls.last.request.content)["data"]["attributes"]["attachment"]
    assert sent == {"content": "aGVsbG8=", "file_name": "a.png"}
    assert out["download_url"] == "https://x/3"


@respx.mock
@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [("2026-10-01", "2026-10-07", "2026-10-01,2026-10-07"), ("2026-10-01", None, "2026-10-01,*")],
)
async def test_user_metrics_date_filter(call, start, end, expected):
    route = respx.get(f"{BASE}/user_metrics").mock(return_value=httpx.Response(200, json={"data": []}))
    await call("search_user_metrics", start_date=start, end_date=end)
    assert route.calls.last.request.url.params["filter[date]"] == expected


@pytest.mark.parametrize(
    ("start", "end"), [(None, "2026-10-07"), ("2026-10-01", "2026-10-20"), ("2026-10-07", "2026-10-01")]
)
async def test_user_metrics_rejects_bad_ranges(call, start, end):
    out = await call("search_user_metrics", start_date=start, end_date=end)
    assert out["error"]["code"] == "invalid_argument"


@respx.mock
async def test_large_results_are_truncated(call):
    rows = [doc("configurations", i, name="x" * 500) for i in range(100)]
    respx.get(f"{BASE}/configurations").mock(return_value=httpx.Response(200, json={"data": rows}))
    out = await call("search_configurations", page_size=100)
    assert out["truncated"] is True and out["has_more"] is True
    assert len(json.dumps(out)) <= 20_500
