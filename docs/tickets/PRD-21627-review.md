# PRD-21627 · Code review

Status: frozen @ 81a3b4d

## Round 1 · 2026-11-05 · reviewed dev/PRD-21627 @ 81a3b4d (base main @ abf9dd7)

Verdict: approved

### Findings

No must-fix findings. Scope: `src/itglue_mcp/tools/flexible_assets.py` (new tool
`itglue_create_flexible_asset_field`), `README.md` (Tools table row + behaviour note),
`tests/fixtures/tools_baseline.json`, `tests/test_middleware.py` (tool-count 40->41),
`tests/test_flexible_assets.py` (7 new tests), `docs/changes/2026-11-05-create-flexible-asset-field.md`.

Checked against `references/mcp-track.md` §4.3 and `legs/review.md` R3:

- Correctness: `itglue_create_flexible_asset_field` builds the request via `api.attributes("flexible_asset_fields", values)` (drops unset values, dasherizes keys, adds JSON:API `"type"`), posts to `/flexible_asset_types/{seg(flexible_asset_type_id)}/relationships/flexible_asset_fields`, flattens with `api.item()` — same pattern as `create_location`/`create_document`/`create_flexible_asset`. `seg()` raises `ToolInputError` for a non-numeric `flexible_asset_type_id` before any HTTP call; `run()` catches it and every `ApiError` path, matching the structured-envelope contract (verified by reading `src/itglue_mcp/tools/_common.py:80-118` and `src/itglue_mcp/api.py:150,233-245`, not just trusting the self-test claim).
- Credentials/isolation: unchanged — one `ITGlueClient` per request bound to the per-call header credentials (`_common.py:80-99`); no new state, no cross-request caching.
- Contract consistency: tool name/params/return/errors match the tech design in `docs/tickets/PRD-21627.md`; `tests/fixtures/tools_baseline.json` widened (not narrowed) in the same commit as the tool, so `test_tool_names_match_baseline`/`test_parameters_are_backward_compatible` cover it.
- Tests follow the change: all 7 new tests in `tests/test_flexible_assets.py` map to AC1-AC7 (cross-checked against `docs/tickets/PRD-21627.ac.json`); `test_middleware.py`'s two hardcoded tool-count assertions were updated (40->41) alongside the new tool, as required.
- Secret handling: `default_value` is masked from error/log output only (via `_field_secrets()`, reused unmodified from `itglue_create_flexible_asset_type`) — the success response and the outbound request are left unmasked. This is a documented, tested deviation from the original tech design (self-test "Deviations" section) and is the same posture the sibling tool already uses; `test_create_flexible_asset_field_error_does_not_leak_default_value` exercises it.
- No new third-party dependency; no schema/migration (this repo is stateless); no change to any existing tool's name, params, or response shape.
- No CJK found in the diff (`git diff abf9dd7..HEAD` scanned for CJK code points — zero hits).
- README's "MSPbots Connector" section is untouched by this diff (only the Tools table row and one behaviour note changed) — out of scope for this review.
- REVIEW.md §2 BLOCKER list: none apply (no migration, no DROP, no duplicate-implementation, no unexplained dependency, no forced push, no int/release-branch contact from this leg yet).

No suggestions beyond what the self-test already documents (pre-existing repo-wide `ruff` issues, unrelated to this diff).
