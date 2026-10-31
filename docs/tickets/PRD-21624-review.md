# PRD-21624 · Code review

## Round 1 · 2026-10-31 · reviewed 83ee746 (base 43e75e6)

Status: frozen @ 83ee746

Verdict: approved

### Scope

`git diff 43e75e6...83ee746` on `MSPbotsAIFramework/itglue-mcp`, `dev/PRD-21624`. Code files touched:
`src/itglue_mcp/api.py`, `src/itglue_mcp/server.py`, `src/itglue_mcp/tools/flexible_assets.py`,
`README.md`, `tests/fixtures/tools_baseline.json`, `tests/test_flexible_assets.py`,
`tests/test_middleware.py`, `docs/changes/2026-10-31-get-flexible-asset-type.md`. Base taken from the
Handoff section of `docs/tickets/PRD-21624.md` ("synced with `main @ 43e75e6`"); confirmed independently
with `git merge-base origin/main 83ee746` == `43e75e6`.

### Verification performed (commands run, not just claims re-read)

- `uv sync && uv run pytest -q` on `83ee746` → **134 passed**, 0 failed. Matches the Self-test section's
  claim exactly (131 on base + 3 new tests).
- `uv run ruff check` / `uv run ruff format --check` scoped to the 5 changed Python files → all clean.
  The three pre-existing lint/format findings the Self-test section lists (`tests/test_passwords.py`,
  `tests/test_handlers.py`, `src/itglue_mcp/_json.py`, `tests/test_paging_offset.py`) are in files this
  ticket does not touch — not this ticket's concern.
- `grep -rnP '[\x{4e00}-\x{9fff}]'` on the 6 changed non-doc files → no matches.
- `README.md` diff is a single one-line hunk in the tools table; the `## MSPbots Connector` marketing
  block is untouched — confirmed with `git diff 43e75e6...83ee746 -- README.md`.
- `tests/fixtures/tools_baseline.json` is valid JSON, 39 entries, matches `test_middleware.py`'s
  `38 -> 39` bump.

### Findings

None. No must-fix, no suggestions.

### Review notes (why this passes, not just that it does)

- **New tool shape**: `get_flexible_asset_type` (`src/itglue_mcp/tools/flexible_assets.py:122-141`) is a
  verbatim match of the Tech design's code block — `seg(id)` numeric-ID guard, `api.item()` +
  the new `api.included()` for the sideload, `run(settings, handler)` wrapper, `READ` annotation,
  `structured_output=False` — same shape as its closest sibling `get_flexible_asset` (`:116-120`).
- **`api.included()`** (`src/itglue_mcp/api.py:183-188`) is a direct sibling of the existing
  `flatten()`/`item()` (same snake-casing, same `drop`-less flatten), adds no new dependency and no new
  abstraction.
- **JSON:API `type` filter value** (`"flexible_asset_fields"`, underscored) matches this repo's
  established (pre-existing) convention for that resource type, used unchanged elsewhere in the same
  file (`flexible_assets.py:36` `_field_relationship_item`, `:233` the `create_flexible_asset` response
  read) — not a new assumption introduced by this ticket.
- **Error handling**: 404 from IT Glue maps to `ApiError("not_found", ...)` in `api.py:48`, caught and
  turned into the structured envelope by `_common.run` (`_common.py:95-96`) — this is existing,
  unmodified framework code; the new tool gets AC2's `not_found` envelope for free, same as every other
  `get_*` tool.
- **AC3 (empty fields)**: the new test mocks a response with no `included` key at all (IT Glue's actual
  omission behaviour per the design, not just an empty array) and asserts `fields == []` — the stronger
  of the two possible test shapes, matches `api.included()`'s `(payload or {}).get("included") or []`
  default.
- **Credentials / AC4**: `get_flexible_asset_type` takes no credential object, reads nothing from
  module scope, and goes through the same per-request `ITGlueClient` construction as every other tool
  (`run()` in `_common.py:92-93`) — no new state, no new isolation risk. Reasonable to rely on the
  existing `credentials.py` test coverage here rather than duplicate it per tool, consistent with how
  PRD-21217 reasoned about its own AC6.
- **Backward compatibility**: purely additive — one new tool, no existing tool's name/params/shape
  changed; `tools_baseline.json` gains exactly one entry, in the right alphabetical slot.
- **Scope**: nothing in the diff is outside the Tech design's Change list; no unrelated files touched.
- **Reuse**: no new dependency, no new HTTP/client/pagination pattern invented; everything new
  (`api.included`) is a direct, minimal extension of existing helpers.

Conclusion: implementation matches the design exactly, self-test claims verified independently
(gates re-run, not just re-read), no scope creep, no missed must-fix categories from
`references/REVIEW.md` §2 or `references/mcp-track.md` §4.3. Approved as-is.
