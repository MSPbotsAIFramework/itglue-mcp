# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Cut pages continue exactly (PRD-21362) and long documents can be read in full (PRD-21363)."""

import json
import re

import httpx
import pytest
import respx
from conftest import BASE

pytestmark = pytest.mark.usefixtures("creds")

CAP = 20_000


def big(type_, i):
    # ~3,000 characters of short fields: shortening long text can't make a page of 50 fit.
    attrs = {"name": f"record {i:04d}", **{f"field_{k}": f"value {k} " * 9 for k in range(30)}}
    return {"id": str(i), "type": type_, "attributes": attrs}


def paged_api(path, rows):
    """Fake IT Glue list endpoint paging by page[number] / page[size], like the real one."""

    def reply(request):
        params = request.url.params
        size, number = int(params["page[size]"]), int(params["page[number]"])
        chunk = rows[(number - 1) * size : number * size]
        total_pages = max((len(rows) + size - 1) // size, 1)
        meta = {"total-count": len(rows), "total-pages": total_pages, "current-page": number}
        return httpx.Response(200, json={"data": chunk, "meta": meta})

    return respx.get(url__regex=rf"{re.escape(BASE + path)}(\?.*)?$").mock(side_effect=reply)


LISTS = [
    ("search_organizations", "/organizations", {}),
    ("search_configurations", "/configurations", {}),
    ("search_passwords", "/passwords", {}),
    ("search_locations", "/locations", {}),
    ("search_flexible_assets", "/flexible_assets", {"flexible_asset_type_id": 21103}),
    ("search_documents", "/organizations/7/relationships/documents", {"organization_id": 7}),
    ("list_document_folders", "/organizations/7/relationships/document_folders", {"organization_id": 7}),
    ("search_user_metrics", "/user_metrics", {}),
]


async def walk(call, tool, args, first=None):
    ids, out, calls = [], None, 0
    start = dict(first or {})
    while True:
        out = await call(tool, **args, **start)
        calls += 1
        assert len(json.dumps(out)) <= CAP + 500
        assert "retry_page_size" not in out
        ids += [r["id"] for r in out["items"]]
        if not out.get("has_more"):
            assert "next_offset" not in out
            return ids, calls
        start = {"offset": out["next_offset"]}
        assert calls < 500


@respx.mock
@pytest.mark.parametrize(("tool", "path", "args"), LISTS)
@pytest.mark.parametrize("page_size", [None, 200])
async def test_cut_pages_walked_by_next_offset_return_every_record_once(call, tool, path, args, page_size):
    rows = [big("x", i) for i in range(60)]
    paged_api(path, rows)
    first = {} if page_size is None else {"page_size": page_size}
    ids, calls = await walk(call, tool, args | first)
    assert ids == [str(i) for i in range(60)]
    assert calls > 2  # pages really were cut


@respx.mock
async def test_walk_from_page_3_returns_every_record_from_that_page_on(call):
    rows = [big("x", i) for i in range(160)]
    paged_api("/organizations", rows)
    ids, _ = await walk(call, "search_organizations", {}, first={"page_number": 3})
    assert ids == [str(i) for i in range(100, 160)]


@respx.mock
@pytest.mark.parametrize(("offset", "page", "first_id"), [(0, 1, 0), (50, 2, 50), (73, 2, 73), (149, 3, 149)])
async def test_offset_reads_the_page_that_holds_it_and_skips_earlier_records(call, offset, page, first_id):
    rows = [{"id": str(i), "type": "x", "attributes": {"name": f"r{i}"}} for i in range(200)]
    route = paged_api("/organizations", rows)
    out = await call("search_organizations", offset=offset)
    assert route.calls.last.request.url.params["page[number]"] == str(page)
    assert out["items"][0]["id"] == str(first_id) and out["offset"] == offset
    assert out["next_offset"] == page * 50


@respx.mock
async def test_offset_past_the_end_is_empty(call):
    paged_api("/organizations", [{"id": "1", "type": "x", "attributes": {}}])
    out = await call("search_organizations", offset=500)
    assert out["items"] == [] and out["has_more"] is False and "next_offset" not in out


@respx.mock
async def test_offset_wins_over_page_number(call):
    rows = [{"id": str(i), "type": "x", "attributes": {}} for i in range(120)]
    route = paged_api("/organizations", rows)
    out = await call("search_organizations", page_number=1, offset=60)
    assert route.calls.last.request.url.params["page[number]"] == "2"
    assert out["items"][0]["id"] == "60"


@respx.mock
async def test_page_number_only_sends_the_same_request_as_before(call):
    rows = [{"id": str(i), "type": "x", "attributes": {}} for i in range(120)]
    route = paged_api("/organizations", rows)
    out = await call("search_organizations", page_number=2, page_size=20)
    params = route.calls.last.request.url.params
    assert (params["page[number]"], params["page[size]"]) == ("2", "20")
    assert [r["id"] for r in out["items"]] == [str(i) for i in range(20, 40)]
    assert (out["page_number"], out["page_size"], out["has_more"], out["total_count"]) == (2, 20, True, 120)


@respx.mock
async def test_name_filter_on_cut_pages_continues_after_the_last_match(call):
    rows = [big("documents", i) for i in range(90)]
    for i, r in enumerate(rows):
        r["attributes"]["name"] = f"runbook {i}" if i % 3 else f"other {i}"
    paged_api("/organizations/7/relationships/documents", rows)
    ids, _ = await walk(call, "search_documents", {"organization_id": 7, "name": "runbook"})
    assert ids == [str(i) for i in range(90) if i % 3]


@respx.mock
async def test_flexible_asset_types_continue_by_offset(call):
    rows = [big("flexible_asset_types", i) for i in range(210)]
    paged_api("/flexible_asset_types", rows)
    ids, _ = await walk(call, "list_flexible_asset_types", {})
    assert ids == [str(i) for i in range(210)]


# ---- PRD-21363: document sections ---------------------------------------------------------------------------


def section(i, content):
    return {"id": str(i), "type": "document-sections",
            "attributes": {"resource-type": "Document::Text", "content": content, "sort": i}}


def document_api(sections):
    respx.get(f"{BASE}/documents/9/relationships/sections").mock(
        return_value=httpx.Response(200, json={"data": sections})
    )
    respx.get(f"{BASE}/organizations/7/relationships/documents/9").mock(
        return_value=httpx.Response(200, json={"data": {"id": "9", "type": "documents", "attributes": {
            "name": "Runbook", "sections": [{"id": s["id"], **s["attributes"]} for s in sections]}}})
    )


@respx.mock
@pytest.mark.parametrize("tool", ["list_document_sections", "get_document"])
async def test_every_section_is_reached_by_next_offset(call, tool):
    document_api([section(i, f"<p>{'step ' * 300}{i}</p>") for i in range(70)])
    args = {"document_id": 9} if tool == "list_document_sections" else {"organization_id": 7, "id": "9"}
    ids, calls = await walk(call, tool, args)
    assert ids == [str(i) for i in range(70)] and calls >= 2


@respx.mock
async def test_a_section_larger_than_the_cap_is_returned_shortened_and_readable_in_parts(call):
    long_html = "".join(f'<p class="x">line {i} with "quotes"</p>' for i in range(4000))
    document_api([section(1, long_html), section(2, "<p>short</p>")])

    out = await call("get_document", organization_id=7, id="9")
    first = out["items"][0]
    assert first["id"] == "1" and first["content_length"] == len(long_html) and out["fields_truncated"] is True
    assert len(json.dumps(out)) <= CAP + 500

    parts, offset, calls = [], 0, 0
    while True:
        part = await call("list_document_sections", document_id=9, section_id=1, content_offset=offset)
        calls += 1
        assert len(json.dumps(part, ensure_ascii=False)) <= CAP and part["content_length"] == len(long_html)
        parts.append(part["section"]["content"])
        if not part["has_more"]:
            assert "next_content_offset" not in part
            break
        offset = part["next_content_offset"]
    assert "".join(parts) == long_html and calls > 1


@respx.mock
async def test_content_offset_past_the_end_is_empty(call):
    document_api([section(1, "<p>hello</p>")])
    part = await call("list_document_sections", document_id=9, section_id=1, content_offset=999)
    assert part["section"]["content"] == "" and part["has_more"] is False


@respx.mock
async def test_unknown_section_is_not_found(call):
    document_api([section(1, "<p>hello</p>")])
    out = await call("list_document_sections", document_id=9, section_id=5)
    assert out["error"]["code"] == "not_found"


@respx.mock
async def test_short_document_is_unchanged(call):
    document_api([section(1, "<p>a</p>"), section(2, "<p>b</p>")])
    out = await call("get_document", organization_id=7, id="9")
    assert [s["id"] for s in out["items"]] == ["1", "2"] and out["has_more"] is False
    assert out["document"]["name"] == "Runbook" and "next_offset" not in out


@respx.mock
async def test_sections_on_later_api_pages_are_read(call):
    # The sections endpoint pages (50 by default; live: 66 sections came back as 50 + 16).
    rows = [section(i, f"<p>{i}</p>") for i in range(66)]

    def reply(request):
        size, number = int(request.url.params["page[size]"]), int(request.url.params["page[number]"])
        size = min(size, 40)  # pretend the API caps the page so a second request is needed
        chunk = rows[(number - 1) * size : number * size]
        more = number * size < len(rows)
        return httpx.Response(200, json={"data": chunk, "meta": {"next-page": number + 1 if more else None}})

    sections_url = rf"{re.escape(BASE)}/documents/9/relationships/sections(\?.*)?$"
    route = respx.get(url__regex=sections_url).mock(side_effect=reply)
    out = await call("list_document_sections", document_id=9, limit=200)
    assert [s["id"] for s in out["items"]] == [str(i) for i in range(66)] and out["total_count"] == 66
    assert [r.request.url.params["page[number]"] for r in route.calls] == ["1", "2"]
