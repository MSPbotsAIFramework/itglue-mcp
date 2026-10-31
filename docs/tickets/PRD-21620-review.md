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

### Round 1 · Fixes (review rework, 2026-10-31)

Fixed the single must-fix (finding 1):

- `docs/tickets/PRD-21620.md` — translated all 6 flagged occurrences to English, in place, pure
  translation with no change to the design's substance:
  - Line 17 (Current state): removed the quoted Chinese sentence from the ticket's "MSPbots 现状"
    note and its own English translation already given inline — the inline translation was kept
    verbatim as the sentence's full text, and the quoted note label itself translated to "MSPbots
    current state".
  - Line 56 (AC4): the quoted Chinese phrase from the ticket's description (`创建 IT Glue 灵活资产类型及其字段`)
    replaced with its English meaning, "create the IT Glue flexible asset type and its fields".
  - Line 64 (Open questions): `[已假设]` → `[assumed]`.
  - Line 65 (Open questions): `[不阻塞]` → `[non-blocking]`; also dropped the redundant Chinese "等"
    next to its own English gloss "etc." in the same bullet.
  - Line 66 (Open questions): `[不阻塞]` → `[non-blocking]`.
  - Also updated the Self-test "Pre-existing issues found but not touched" bullet (original line
    321-330, not itself one of the 6 flagged lines) so it no longer quotes the original Chinese
    phrase or bracket tags verbatim — it now describes them without reproducing the characters, and
    states the issue was found pre-existing by this ticket's own design commit, flagged by this
    review round, and fixed here. This bullet was not in the finding's line list but quoted the same
    text and would otherwise go stale and still fail the grep gate after the fix; translating it is
    the same no-substance-change class of edit the finding authorized, not a new must-fix (same
    precedent as `docs/tickets/PRD-21217.md` round 1's equivalent bullet).
  - Did not change the frozen header SHA reference mechanism: `docs/tickets/PRD-21620.md` carries
    `Status: frozen @ e5d28c5` from the original dev leg; this review-rework edit is layered on top
    per `legs/dev.md` S1 "评审返工" (fix on the same branch, document the fix in this review file,
    main document otherwise left alone).
- Verification: `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .` now
  returns **zero matches in `docs/tickets/PRD-21620.md`**, and zero matches anywhere outside this
  review file. The only remaining Chinese in the repository is in this file's own Round 1 findings
  above (the reviewer's verbatim citation of the original defect text and of this pipeline's own
  Chinese-language internal SOP/reference docs as evidence) — the historical record of what round 1
  found, left unedited (review findings are not revised after the fact); it is not product code,
  design content, or documentation the repo ships. Same acceptance as
  `docs/tickets/PRD-21217-review.md` round 1's equivalent note.
- Gates re-run on the fixed commit (docs-only change; code and tests untouched since round 1):
  `uv sync` — 0; `uv run pytest -q` — **129 passed**, 0 failed; `uv run ruff check .` / `uv run ruff
  format --check .` on the full tree — same pre-existing baseline as round 1 (3 lint errors / 3
  files needing reformat, none in files this ticket's dev leg touched or added); no source or test
  file was changed in this round, so no new scoped lint surface exists.
- Test cases: unaffected by a docs-only fix — all 9 cases (TC-IGT-001..009) remain as recorded in
  the original Self-test (`.ac.json` unchanged, `result`/`evidence` fields untouched).

## Round 2 · 2026-10-31 · reviewed dev/PRD-21620 @ a191c6a (base main @ 788bcac)

Status: frozen @ a191c6a

Verdict: approved

### Fix verification (round 1 finding 1)

- Confirmed the diff between the round-1 reviewed commit and this one
  (`git diff 00391ae..a191c6a`) touches only `docs/tickets/PRD-21620.md` and
  `docs/tickets/PRD-21620-review.md` — no source or test file changed, matching the dev leg's
  own claim that this was a docs-only translation round.
- Read every one of the 6 edits line by line against the round-1 finding: each is a direct,
  meaning-preserving translation (`[已假设]` → `[assumed]`, `[不阻塞]` → `[non-blocking]` ×2, the
  AC4 and Current-state quoted phrases replaced by their English meaning already established
  inline, the redundant Chinese "等" dropped next to its own English gloss). No AC, scope, or
  conclusion text changed — this is translation, not a design rewrite, so it did not need to go
  back to the design leg.
- Independently re-ran `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .`
  on `a191c6a`: **zero matches outside this review file**, and zero matches in
  `docs/tickets/PRD-21620.md` itself. The only remaining Chinese in the tree is this review file's
  own Round 1 verbatim citation of the original defect text, which is a historical record of a
  past finding, not product code, design content, or documentation the repo ships — same
  acceptance as `docs/tickets/PRD-21217-review.md`.
- Independently re-ran the gates on `a191c6a`: `uv sync` → 0; `uv run pytest -q` → **129 passed,
  0 failed**; `uv run ruff check .` and `uv run ruff format --check .` on the full tree → 3
  pre-existing errors / 3 pre-existing files needing reformat (`tests/test_handlers.py`,
  `tests/test_passwords.py` for check; `src/itglue_mcp/_json.py`, `tests/test_handlers.py`,
  `tests/test_paging_offset.py` for format) — none of these five files are in this ticket's diff
  (`git diff 788bcac..a191c6a --name-only`), confirming the baseline is unrelated and unchanged by
  this round. No new must-fix.
- No new findings. Round 1's "What passed review" section (correctness, AC1-AC8, reuse, backward
  compatibility, README Connector section, no migration, no cross-repo dependency) is unaffected
  by a docs-only round and still holds — spot-checked `src/itglue_mcp/tools/flexible_assets.py`
  (`_field_relationship_item`, `itglue_create_flexible_asset_type`) and
  `src/itglue_mcp/api.py:233-246` (`attributes()` with `relationships`) again directly; unchanged
  since round 1 and still additive/backward-compatible.

Conclusion: the single must-fix from round 1 is fixed and independently verified; no new
must-fix. Approved for merge into `main`, INT publish, and connector wiki check.
