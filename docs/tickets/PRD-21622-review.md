# PRD-21622 · Code review

Status: frozen @ 8dfb478

## Round 1 · 2026-11-05 · reviewed dev/PRD-21622 @ 8dfb478 (base abf9dd7)

Verdict: approved

### Findings

None. Scope matches the tech design exactly (two new optional parameters, `organization_id: int | None` and `restricted: bool | None`, on the existing `update_flexible_asset` tool); no required parameter added, no other tool touched, no new dependency.

Verified directly (not just read from the Self-test section):
- `src/itglue_mcp/tools/flexible_assets.py:188-203` — both new fields flow into the same `values` dict consumed by `api.attributes()` (drop-`None`, dasherize), same pattern as the existing `archived` field; `restricted=False` is not conflated with "not provided" since only `None` is filtered.
- `tests/test_flexible_assets.py` — 4 new tests cover AC1-AC3 and the old+new combination; pre-existing regression tests for AC4 (`test_update_flexible_asset_sends_only_changed_fields`), AC5 (`test_update_flexible_asset_rejects_empty_call`), AC6 (`test_update_flexible_asset_not_found_returns_envelope`) are unmodified.
- `tests/fixtures/tools_baseline.json:399-405` — baseline's `update_flexible_asset.params` updated to include `organization_id`/`restricted`; `required` unchanged (`["id"]`), consistent with `AGENTS.md`'s "no new required parameter" rule and `tests/test_tools.py::test_parameters_are_backward_compatible`.
- `src/itglue_mcp/credentials.py:1-35` — credentials remain per-request (`ContextVar`), this change adds no module-level or cross-request state (AC7).
- `src/itglue_mcp/tools/flexible_assets.py:23-26` (`_trait_secrets`) — `organization_id`/`restricted` are plain int/bool, correctly not run through the trait-secret masking (neither is secret-shaped).
- Re-ran the gate on this tree: `uv run pytest -q` → `144 passed`, matching the Self-test section's claim.
- Chinese-text scan (`grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .`) → no matches in any file this ticket touched.
- README Connector section (`README.md:13-81`) diffs clean against `~/.claude/skills/vendor-mcp-development/reference/readme-connector-section.md` (byte-for-byte, aside from the surrounding `<div align="center">` wrapper lines which are outside the diffed range) — unaffected by this change, consistent with the design's "no README change" claim.
- `docs/changes/2026-11-04-update-flexible-asset-organization-and-restricted.md` present, follows the format of the prior entry for this repo.

No must-fix, no suggestions.
