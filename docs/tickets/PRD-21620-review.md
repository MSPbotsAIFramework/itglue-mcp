# PRD-21620 · Code review

## Round 1 · 2026-10-31 · reviewed dev/PRD-21620 @ ea0b5cc (base main @ 788bcac)

Verdict: changes requested

### Findings

1. [must-fix] docs/tickets/PRD-21620.md:17,56,64,65,66,323 — the design document introduced by
   this ticket's own branch (commit `dead110`) contains Chinese text: a quoted Chinese phrase in
   "Current state" (line 17, partially translated inline but the Chinese substring itself is still
   present), a quoted Chinese phrase in AC4 (line 56, no translation given), two bracket tags under
   "Product design > Open questions" meaning "assumed" and "non-blocking" (lines 64-66), and a
   Self-test bullet (line 323) that quotes those same bracket tags verbatim. This repo is an
   MSPbotsAIFramework vendor MCP repo, which must be entirely English (SOP §0.4; SOP §14 checklist
   item "仓库内容全部英文 ... 均无中文"; `references/mcp-track.md` §4.3 lists "仓库里没有中文" as a
   condition where any failure is a must-fix). This is the same class of finding as
   `docs/tickets/PRD-21217-review.md` Round 1 finding 1 on this same repo (2026-10-30): the
   division of labour between design and dev/review legs over *who owns the wording* does not
   change that the repo-wide "no Chinese anywhere" checklist item is a hard gate review must
   enforce. The dev leg's own Self-test (line 321-330 context) already found and flagged this
   exact defect, attributing it to the design leg's commit and correctly declining to edit the
   design document itself — but flagging is not fixing, and the repo as it stands in this diff
   still fails
   `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .` (6 matches, verified
   independently by this review, all 6 confined to `docs/tickets/PRD-21620.md`, zero elsewhere in
   the tree). Fix: per the PRD-21217 precedent, replace all 6 occurrences with English text (direct
   translations that preserve meaning without altering the design's substance — e.g. the bracket
   tags become `[assumed]` / `[non-blocking]`, the quoted Rewst/AC phrases become their English
   meaning, already given inline for line 17 and needed fresh for line 56), rerun the grep to
   confirm zero matches anywhere in the repo, and note the fix in the next Self-test update. This
   does not require reopening product design (no AC, scope, or conclusion changes) — it is the same
   non-substantive translation class of edit the PRD-21217 round-1 rework made, layered on top of
   the existing frozen `docs/tickets/PRD-21620.md` without changing its frozen header mechanism.

### What passed review (no must-fix)

- **Correctness**: `api.attributes()`'s new `relationships` parameter (`src/itglue_mcp/api.py:233-246`)
  defaults to `None` and is additive — verified both existing call sites
  (`create_flexible_asset`, `update_flexible_asset`) are untouched and their own tests pass
  unmodified (`tests/test_api.py::test_attributes_without_relationships_unchanged`,
  `::test_attributes_with_resource_id_unchanged`). `_field_relationship_item()`
  (`src/itglue_mcp/tools/flexible_assets.py:29-36`) validates `name`/`kind` per field and raises
  `ToolInputError` *before* any HTTP call (AC5), matching `update_flexible_asset`'s existing
  "validate before request" pattern; confirmed by
  `test_create_flexible_asset_type_rejects_field_missing_kind` /
  `_rejects_field_missing_name`, both asserting no `respx` route needs to exist.
- **AC1-AC4 (request shape)**: `test_create_flexible_asset_type_name_only`,
  `_forwards_all_attributes`, `_omits_unset_optional_attributes`,
  `_sends_fields_relationship`, `_without_fields_omits_relationships`, and
  `_with_empty_fields_list_omits_relationships` each assert the exact JSON body sent to `respx`,
  not just the tool's return value — this is the strongest form of request-shape evidence this
  repo's test style supports, and it matches the design's AC1-AC4 wording exactly.
- **AC7 (no secret leakage)**: `_field_secrets()` (`flexible_assets.py:38-45`) collects a field's
  `default_value` the same way `_trait_secrets()` already does for `traits`, and
  `test_create_flexible_asset_type_error_does_not_leak_default_value` forces a bare `RuntimeError`
  (the path that would otherwise log a full traceback) and asserts the secret-looking value is
  absent from both the JSON response and `caplog` — same proof pattern as the existing
  `test_create_flexible_asset_error_does_not_leak_trait_values`.
- **AC8 (tool metadata)**: `CREATE` annotation (`readOnlyHint=False, destructiveHint=False,
  idempotentHint=False`) reused unchanged from `tools/_common.py:22`, asserted directly in
  `test_tools.py::test_annotations`; no `agent_id` parameter (covered generically by
  `test_no_agent_id_parameter`, which iterates every registered tool); `README.md:107`'s Tools
  table row updated; `tests/fixtures/tools_baseline.json` only gains one entry, no existing entry
  narrowed (confirmed by diff).
- **Reuse / no duplication**: the one new piece of shared machinery (`relationships` on
  `api.attributes()`) is an additive extension of the single existing JSON:API body builder, not a
  second body-building path — matches the tech design's "Option analysis" rejection of an ad hoc
  builder. `_field_secrets()` is a natural one-field-source sibling of `_trait_secrets()`, not a
  duplicate (different source dict, same posture) — acceptable per `references/mcp-track.md` §7a.
- **Backward compatibility**: `tests/test_middleware.py`'s hardcoded tool-count bump (37 → 38) is
  the correct, minimal, mechanical consequence of one tool addition (same recurring gap
  `docs/tickets/PRD-21586.md` already flagged); independently re-verified by this review as exactly
  2 lines changed, no other assertion touched.
- **README Connector section**: `README.md` lines 11-81 diffed byte-for-byte against
  `~/.claude/skills/vendor-mcp-development/reference/readme-connector-section.md` by this review —
  identical. Only the Tools-table row and one new behaviour note were added, both outside that
  block.
- **Gates, independently re-run by this review on `ea0b5cc`** (not just trusted from Self-test):
  `uv sync` → 0; `uv run pytest -q` → **129 passed, 0 failed**; `uv run ruff check` and
  `uv run ruff format --check`, scoped to every file this ticket touched or added
  (`api.py`, `flexible_assets.py`, `test_flexible_assets.py`, `test_api.py`, `test_tools.py`,
  `test_middleware.py`) → both clean. Matches the dev leg's own report exactly.
- **Chinese-text scan, independently re-run by this review**:
  `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .` → 6 matches, all in
  `docs/tickets/PRD-21620.md` (see Finding 1), zero in any code, test, README, or changelog file
  this ticket touches — the Self-test's own scoped claim ("zero matches" for files the dev leg
  changed or added) is accurate; the repo-wide gate is what fails, and the dev leg correctly
  flagged rather than hid it.
- **No migration / schema**: this repo is stateless, confirmed no DB/migration files exist or are
  touched — `REVIEW.md` §2 items 5 and 11 do not apply.
- **No cross-repo header/field compatibility concern** (`references/mcp-track.md` §1.2): this
  ticket touches a single MCP repo with no platform or sibling-MCP dependency.
