# PRD-21625 · Code review

## Round 1 · 2026-11-05 · reviewed dev/PRD-21625 7fbba08 (base main abf9dd7)

Verdict: approved

### Findings

No must-fix findings.

1. [suggestion] `src/itglue_mcp/tools/contacts.py:30` — the module docstring doesn't carry a `(PRD-21625)` suffix the way `users.py`'s module-level additions from the sibling ticket PRD-21586 do elsewhere in this repo's history; purely cosmetic, no action needed.
2. [suggestion] `docs/tickets/PRD-21625.md` Self-test "Pre-existing issues found but not touched" — the prose attributes both non-`E501` `ruff` errors to `tests/test_passwords.py` ("I001 import-sort issue in `tests/test_passwords.py` (2 of the 3 reported errors)"), but independently re-running `uv run ruff check .` on `HEAD` shows the 3 pre-existing errors are actually split across two files: one `I001` in `tests/test_handlers.py:5` (already present, unchanged, in `main@abf9dd7`) and one `I001` + the `E501` in `test_handlers.py`/`test_passwords.py` respectively — the total count (3) and "0 introduced by this ticket" conclusion are both correct, only the per-file breakdown in the prose is slightly off. No functional impact; not corrected since the main doc is frozen and this doesn't change any AC or gate result.

### Independent verification (this review round)

- `uv run pytest -q` on `dev/PRD-21625@7fbba08`: **146 passed**, 0 failed — matches the Self-test's `final` gate.
- `uv run ruff check .`: 3 pre-existing errors (`I001` x2, `E501` x1), confirmed identical to `main@abf9dd7` via `git show abf9dd7:tests/test_handlers.py` import-block diff (no change) — 0 new issues on touched files.
- `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv --exclude-dir=docs .` → no matches.
- Live smoke (`uv run itglue-mcp`, `127.0.0.1:8080`): `GET /health` → `200 {"status":"ok"}`; `tools/list` without `X-ITGlue-API-Key` → `401`; with a placeholder key → `200`, 41 tools, `itglue_list_contacts` present with `readOnlyHint: true`, no `agent_id` parameter, params match `tools_baseline.json`'s new entry.

### Review notes

- **Correctness**: `itglue_list_contacts` (`src/itglue_mcp/tools/contacts.py:42-85`) reuses the shared `locate()`/`run()`/`api.page()` plumbing every other list tool in this connector uses; `None` filter values are dropped generically by `ITGlueClient.request()` (`src/itglue_mcp/api.py:117`), so no special-casing was needed or added.
- **Scope**: purely additive — one new tool, a 2-line `server.py` registration, README table/behaviour-note update, and the mechanical test/baseline updates the addition requires. No existing tool's behaviour changed.
- **Reuse**: no new dependency; follows the exact shape of `organizations.py`/`users.py`.
- **Security**: credentials unchanged (header-only, per-request `ITGlueClient`, no caching); contacts carry no secret fields, consistent with the design's "no `drop` set needed" call.
- **Tests**: all 8 ACs (`TC-IGLC-001..008`) have evidence in `docs/tickets/PRD-21625.ac.json`; filter-forwarding, pagination and tool-count assertions verified independently above.
- **Design deviations** (documented in Self-test, both reasonable): `test_middleware.py`'s hardcoded count landed at `40 -> 41` instead of the design's stated `37 -> 38` because four sibling tickets (PRD-21620/21621/21624/21626) merged into `main` between design and dev; and `test_tools.py` got one extra direct `readOnlyHint` assertion not in the original Change list. Both verified against the current tree, no AC impact.

Status: frozen @ 7fbba08
