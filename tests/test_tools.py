# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""tools/list contract: names and parameters must stay compatible with the registered connector."""

import json
from pathlib import Path

BASELINE = json.loads((Path(__file__).parent / "fixtures" / "tools_baseline.json").read_text())


async def _tools(mcp):
    return {t.name: t for t in await mcp.list_tools()}


async def test_tool_names_match_baseline(mcp):
    assert set(await _tools(mcp)) == set(BASELINE)


async def test_parameters_are_backward_compatible(mcp):
    tools = await _tools(mcp)
    for name, expected in BASELINE.items():
        schema = tools[name].inputSchema
        props = set(schema.get("properties", {}))
        required = set(schema.get("required", []))
        assert set(expected["params"]) <= props, f"{name} lost parameters"
        assert required <= set(expected["required"]), f"{name} gained required parameters"


async def test_descriptions_are_concise(mcp):
    for tool in (await _tools(mcp)).values():
        assert tool.description and len(tool.description) <= 500, tool.name


async def test_annotations(mcp):
    tools = await _tools(mcp)
    destructive = (
        "delete_document", "delete_document_section", "archive_document", "unarchive_document", "delete_attachment",
    )
    for name in destructive:
        assert tools[name].annotations.destructiveHint is True, name
    for name in ("search_organizations", "get_password", "itglue_health_check", "list_attachments"):
        assert tools[name].annotations.readOnlyHint is True, name
    new_type_tool = tools["itglue_create_flexible_asset_type"].annotations
    assert new_type_tool.readOnlyHint is False
    assert new_type_tool.destructiveHint is False
    assert new_type_tool.idempotentHint is False


async def test_no_agent_id_parameter(mcp):
    # The platform injects its own value into parameters named agent_id.
    for tool in (await _tools(mcp)).values():
        assert "agent_id" not in tool.inputSchema.get("properties", {}), tool.name
