# Copyright 2026 MSPbots.ai
# SPDX-License-Identifier: Apache-2.0
"""Direct coverage of api.attributes()'s JSON:API document builder (PRD-21620)."""

from itglue_mcp import api


def test_attributes_without_relationships_unchanged():
    doc = api.attributes("flexible_assets", {"organization_id": 3, "name": "x", "skip": None})
    assert doc == {"data": {"type": "flexible_assets", "attributes": {"organization-id": 3, "name": "x"}}}
    assert "relationships" not in doc["data"]


def test_attributes_with_resource_id_unchanged():
    doc = api.attributes("flexible_assets", {"name": "x"}, resource_id=789)
    assert doc == {"data": {"type": "flexible_assets", "id": "789", "attributes": {"name": "x"}}}
    assert "relationships" not in doc["data"]


def test_attributes_with_relationships_nests_data():
    doc = api.attributes(
        "flexible_asset_types",
        {"name": "BitLocker (Rewst)"},
        relationships={
            "flexible-asset-fields": [
                {"type": "flexible_asset_fields", "attributes": {"name": "BitLocker Keys", "kind": "Textbox"}}
            ]
        },
    )
    assert doc == {
        "data": {
            "type": "flexible_asset_types",
            "attributes": {"name": "BitLocker (Rewst)"},
            "relationships": {
                "flexible-asset-fields": {
                    "data": [
                        {"type": "flexible_asset_fields", "attributes": {"name": "BitLocker Keys", "kind": "Textbox"}}
                    ]
                }
            },
        }
    }


def test_attributes_with_empty_relationships_dict_omits_key():
    doc = api.attributes("flexible_asset_types", {"name": "x"}, relationships={})
    assert "relationships" not in doc["data"]
