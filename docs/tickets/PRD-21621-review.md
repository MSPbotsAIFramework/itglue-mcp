# PRD-21621 · Code review

## Round 1 · 2026-10-31 · reviewed dev/PRD-21621 @ 791c08e (base main @ 788bcac)

Verdict: approved

### Findings

No must-fix findings.

1. [suggestion] `tests/fixtures/tools_baseline.json` — the baseline widening for `create_flexible_asset` (adding `archived`, `restricted` to `params`) was re-serialized with the file's existing one-space indent style; confirmed the diff is limited to the single changed entry (`git diff --stat`: 2 insertions). No action needed, noted only because the design flagged this as something for review to double-check independently.

### Verification performed

- `git diff 788bcac...791c08e --stat` — 7 files changed, 652 insertions, 1 deletion; touches `README.md`, `docs/changes/...`, `docs/tickets/PRD-21621.{md,ac.json}`, `src/itglue_mcp/tools/flexible_assets.py`, `tests/fixtures/tools_baseline.json`, `tests/test_flexible_assets.py`. Scope matches the tech design's Change list exactly — no out-of-scope files touched.
- Read `src/itglue_mcp/tools/flexible_assets.py:101-126` (`create_flexible_asset`) and `src/itglue_mcp/api.py:233-239` (`api.attributes`): confirmed `archived`/`restricted` are folded into the same `values` dict as the existing optional parameters, and `api.attributes` drops `None` values before building the POST body — so omitting both parameters produces a byte-for-byte unchanged request (AC1/AC4), matching the existing pattern `update_flexible_asset` already uses for `archived` (`flexible_assets.py:128-151`).
- Ran `uv sync && uv run pytest -q` myself on `dev/PRD-21621 @ 791c08e`: **117 passed, 0 failed** — matches the Self-test section's claim exactly (115 on `main@788bcac` + 2 new tests).
- Ran `uv run ruff check` / `uv run ruff format --check` on the two touched source files (`flexible_assets.py`, `test_flexible_assets.py`): both clean. The three pre-existing lint/format issues the Self-test section lists as baseline-only (`tests/test_handlers.py`, `tests/test_passwords.py`, `src/itglue_mcp/_json.py`, `tests/test_paging_offset.py`) are untouched by this diff — not this ticket's concern.
- Ran a Chinese-text scan (`grep -rnP '[\x{4e00}-\x{9fff}]'`) over the full tree: no matches.
- Independently constructed the live MCP tool schema for `create_flexible_asset` (`FastMCP.list_tools()` against the registered tool) instead of trusting the Self-test's smoke-test transcript: `required` is exactly `["organization_id", "flexible_asset_type_id"]` (unchanged — no new required parameter, satisfying `AGENTS.md`'s "do not add required parameters"); `archived` and `restricted` both appear as `{"anyOf": [{"type": "boolean"}, {"type": "null"}], "default": None}`. Matches AC2/AC3's shape and AC1/AC4's backward-compatibility claim exactly.
- Checked `_trait_secrets` (`flexible_assets.py:23-26`): unchanged, still scans only `traits` values. `archived`/`restricted` are plain booleans and correctly not added to the secrets list — no credential/secret handling regression (AC7, re-verified by `test_create_flexible_asset_error_does_not_leak_trait_values` passing with the two new parameters also set).
- Confirmed via the diff that the `## MSPbots Connector` marketing block (lines 1-~100 of `README.md`) is untouched; the only `README.md` hunk is a single 3-line addition under "Behaviour notes" (line 131), consistent with `reference/readme-connector-section.md`.
- Design's evidence for `restricted` being a real, accepted `POST /flexible_assets` attribute (IT Glue's public API docs, fetched 2026-10-31) is cited with a URL and is consistent with this repo's existing citation of the same source (`api.py:5`); flagged in the design as a documented, non-blocking risk (no test account to verify live) — correctly carried through to `ac.json` TC6 as `result: untested` with a reason, not a false "pass".

### Review checklist (`legs/review.md` R3 / MCP additions, `references/mcp-track.md` §4.3)

- Correctness: boolean passthrough, `None`-dropped by existing `api.attributes` — verified above, no edge case missed (empty string, 0, False are all distinguishable from `None` for `bool | None`, so `archived=False` still reaches IT Glue, consistent with AC2/AC3's "sets" wording literally meaning "whatever truthy/falsy value was passed").
- Scope: no file outside the tech design's Change list touched; no other tool's behaviour changed.
- Reuse: 100% reuse of `api.attributes`/`api.item`; no new dependency; follows the in-repo `update_flexible_asset` precedent exactly, as the tech design states.
- Security: credentials still per-request from `X-ITGlue-API-Key` (unchanged); no secret-bearing field touched; no logging change.
- Tests: all 7 ACs have either a passing automated test with reproducible evidence, or (TC6) an honestly recorded `untested` with a stated reason that matches the known, documented exemption (`references/mcp-track.md` §3: missing vendor test account is not a blocker). No test was weakened or reinterpreted to pass.
- `REVIEW.md` BLOCKER list: none apply — no schema/migration (MCP repo has none), no bypass flags used, no forced push, basis (`main@788bcac`) was freshly fetched at review time and matches the `[DEV]` stub's recorded base (no re-sync needed before merge).
- README Connector section: untouched, matches the reference file (this ticket did not need to touch the marketing block).
- No duplicate implementation of an existing component; no undeclared new dependency (none added).

### Fixes

N/A — no must-fix findings, nothing to fix.

---

Status: frozen @ 791c08e
