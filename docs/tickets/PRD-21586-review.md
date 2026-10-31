# PRD-21586 · Code review

## Round 1 · 2026-10-31 · reviewed dev/PRD-21586 @ 0dc3e96 (base main @ 2f757b1)

Verdict: approved

### Findings

No must-fix. No suggestions — the change is a minimal, additive tool that reuses every existing
helper (`locate()`, `run()`, `api.page()`/`flatten()`) with no new abstraction, no new dependency,
and no deviation from the repo's established `search_organizations`/`search_locations` shape.

### Verification performed

- `git diff origin/main...HEAD --stat`: 10 files changed, 552 insertions, 2 deletions — scoped to
  `README.md`, `src/itglue_mcp/{server.py,tools/users.py}`, `tests/{test_handlers.py,
  test_middleware.py,test_paging_offset.py,fixtures/tools_baseline.json}`,
  `docs/tickets/PRD-21586.{md,ac.json}`, `docs/changes/2026-10-31-list-account-users.md`. No file
  outside the ticket's stated scope was touched.
- Correctness: `users.py` follows `organizations.py:15-52` exactly — `locate()` builds paging
  params, filters (`filter[name]`, `filter[email]`, `filter[role_name]`, `sort`) are forwarded
  as-is (unset ones are dropped by `ITGlueClient.request`'s `clean = {k: v for k, v in ... if v is
  not None and v != ""}`, `api.py:117`), `api.page()` flattens the JSON:API response. No new error
  paths, no new state, nothing is cached across requests.
- Security/multi-tenant: unchanged credential model — one `ITGlueClient` per request, API key
  read from header only (`api.py:89-99`); `/users` has no secret-shaped fields, so the "no drop set
  needed" decision in Self-test's Reuse & cleanup section is correct (compared against
  `passwords.py`'s `SECRET_FIELDS` pattern, which does need one).
- Backward compatibility: `tools_baseline.json` only gained an entry (verified by diff — no
  existing entry's `params`/`required` changed); `test_middleware.py`'s two hardcoded tool-count
  assertions (36 → 37) are the correct, minimal, mechanical consequence of a purely additive tool
  and were not part of the original tech design's change list but are flagged as such in Self-test
  — correctly surfaced, not smuggled in.
- Ran the gates myself, on `dev/PRD-21586 @ 0dc3e96` after `uv sync`:
  - `uv run pytest -q` → **115 passed**, matches the Self-test claim exactly.
  - `uv run ruff check` scoped to touched/new files (`users.py`, `server.py`, `test_middleware.py`,
    `test_paging_offset.py`, `test_handlers.py`, `README.md`) → 2 errors, both in
    `tests/test_handlers.py` (import-sort at the top of the file, `E501` inside
    `test_create_document_with_content_adds_section_and_publishes` at line 221) — neither line is
    touched by this ticket's diff (new tests are appended after line 37).
  - `uv run ruff format --check` on the same scope → `test_handlers.py` and `test_paging_offset.py`
    flagged, same pre-existing locations (`test_error_mapping`, `test_delete_document`,
    `create_attachment` call, `section()` helper) — not the new `users.py` code.
  - Re-ran both ruff commands against a separate pristine `origin/main@2f757b1` worktree: **same 3
    ruff-check errors, same 3 files needing reformat** — confirms these are baseline, not
    introduced by this ticket, and that the increment is zero. Matches Self-test's own claim
    exactly.
  - Chinese-text scan: clean.
  - Live smoke test (`uv run itglue-mcp`, port 8080): `/health` → `200`; `POST /mcp initialize`
    with no `X-ITGlue-API-Key` → `401`; `tools/list` with a placeholder key → `200`, **37 tools**,
    `itglue_list_account_users` present with `readOnlyHint: true` and no `agent_id` parameter.
    Matches Self-test's claims exactly.
- README: only the `Tools` table (`Users` row) and one behaviour note were added; the
  `## MSPbots Connector` block is untouched, confirmed by diff.
- Design-to-code mapping: all 7 ACs (AC1–AC7) trace to one test each in `.ac.json`, each with a
  concrete command + output as evidence, not a bare "pass". No use case tests implementation
  details instead of the stated behaviour.

### Conclusion

Implementation matches the tech design with no unauthorized scope creep, no new dependency, and no
behavioural change to any existing tool. Self-test's claims were independently reproduced
end-to-end (test count, lint/format baseline delta, live tool count and annotations). Approved for
merge.

Status: frozen @ 0dc3e96
