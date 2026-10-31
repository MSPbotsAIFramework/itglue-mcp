# PRD-21626 · Code review

## Round 2 · 2026-10-31 · reviewed dev/PRD-21626 @ ec4cf51 (base ae5c844)

Status: frozen @ ec4cf51

Verdict: approved

### Findings

None. Scope for this round is the round-1 must-fix only (`tests/test_tools.py:36-42` ruff format),
plus the "Fixes" section appended to this file in the same commit (`ec4cf51`). Verified
independently against the review's own commands (not just re-stating the diff's claims):

- `uv run ruff format --check .` on `dev/PRD-21626 @ ec4cf51`: 4 files flagged
  (`docs/tickets/PRD-21624.md`, `src/itglue_mcp/_json.py`, `tests/test_handlers.py`,
  `tests/test_paging_offset.py`) — same as independently re-run on pristine base `ae5c844`
  (also 4, same files). `tests/test_tools.py` no longer appears. Round-1 must-fix is fixed.
- `uv run ruff check .`: 3 errors on both `ae5c844` and `ec4cf51` — same 3 lines
  (`tests/test_handlers.py:5` `I001`, `tests/test_handlers.py:221` `E501`,
  `tests/test_passwords.py:5` `I001`), 0 new. Matches round 1's own finding-3 correction.
- `uv run pytest -q`: 140 passed, 0 failed on `ec4cf51` — no regressions.
- Chinese-text scan (`grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .`):
  no hits outside the pre-existing `docs/tickets/PRD-2162*.md` files.
- `git diff ae5c844...ec4cf51 --stat`: touches only the 9 files round 1 already reviewed plus the
  review doc itself (`README.md`, `docs/tickets/PRD-21626{.ac.json,.md,-review.md}`,
  `src/itglue_mcp/tools/attachments.py`, `tests/{fixtures/tools_baseline.json,test_handlers.py,
  test_middleware.py,test_tools.py}`) — no new files, no scope creep from the round-1 fix.
- The two round-1 suggestions (`docs/changes/` entry; Self-test's `ruff check` file-attribution
  typo) were left unaddressed, as the Fixes section says. Both remain suggestions, not must-fix —
  the `docs/changes/` convention gap is a repo-convention nit, not a BA-acceptance or runtime risk;
  the Self-test typo is already corrected in this file (round 1 finding 3) for any future reader.

No new must-fix. Approved.

## Round 1 · 2026-10-31 · reviewed dev/PRD-21626 @ 7e5d2c5 (base ae5c844)

Verdict: changes requested

### Findings

1. [must-fix] tests/test_tools.py:36-42 — this ticket's own new code fails the repo's declared lint
   gate. `AGENTS.md`'s `## Commands` section defines lint as
   `uv run ruff check . && uv run ruff format --check .` (both halves, chained). The Self-test
   section of `docs/tickets/PRD-21626.md` only ran and reported `uv run ruff check .`; it never ran
   `ruff format --check .`, so this half of the declared gate was silently skipped.
   Verified independently: `uv run ruff format --check .` on the pristine base (`ae5c844`) flags 4
   pre-existing files (`docs/tickets/PRD-21624.md`, `src/itglue_mcp/_json.py`,
   `tests/test_handlers.py`, `tests/test_paging_offset.py`); on `dev/PRD-21626 @ 7e5d2c5` it flags
   5 — the same 4 plus `tests/test_tools.py`, which is exactly the file this ticket's diff touched
   (the new `destructive = (...)` tuple added to `test_annotations` for AC6 coverage). This is a
   new gate failure introduced by this change, per `REVIEW.md` §2 item 1 (declared gate command
   non-zero exit, not covered by any §4 exemption).
   Fix: run `uv run ruff format tests/test_tools.py` (wraps the tuple one item per line, matching
   ruff's formatter — see the `--diff` output below) and re-verify `uv run ruff format --check .`
   reports only the same 4 pre-existing files, no new ones.
   ```
   --- tests/test_tools.py
   +++ tests/test_tools.py
   @@ -34,7 +34,11 @@
    async def test_annotations(mcp):
        tools = await _tools(mcp)
        destructive = (
   -        "delete_document", "delete_document_section", "archive_document", "unarchive_document", "delete_attachment",
   +        "delete_document",
   +        "delete_document_section",
   +        "archive_document",
   +        "unarchive_document",
   +        "delete_attachment",
        )
        for name in destructive:
    ```

2. [suggestion] docs/changes/ — `AGENTS.md`'s `## Rules` section says "Record changes in
   `docs/changes/` and releases in `docs/releases/`." Every prior ticket on this connector that
   added a tool has a `docs/changes/2026-10-3x-<slug>.md` entry (PRD-21620, PRD-21621, PRD-21624,
   etc. — see `docs/changes/2026-10-31-get-flexible-asset-type.md` for the shape). This ticket's
   diff adds none for `delete_attachment`. Not a BA-acceptance or runtime risk by itself, but it
   breaks a repo convention every sibling ticket has followed; worth adding in the same pass as the
   fix above.

3. [suggestion] docs/tickets/PRD-21626.md (Self-test · Gates) — the claim "`uv run ruff check .`:
   3 pre-existing errors only ... all in `tests/test_passwords.py` (import-sort/`I001`)" is
   factually wrong, independently of finding 1. Re-running `uv run ruff check .` on both
   `ae5c844` and `dev/PRD-21626 @ 7e5d2c5` gives the same 3 errors in both cases (so the "0
   introduced by this ticket" conclusion for `ruff check` itself still holds), but only 1 of the 3
   (`tests/test_passwords.py:5`, `I001`) is in that file — the other two
   (`tests/test_handlers.py:5` `I001`, `tests/test_handlers.py:221` `E501`) are not. Worth
   correcting the record so a future reader doesn't rule out `test_handlers.py` as a source of
   pre-existing lint noise.

### What was verified independently (not just re-stating the Self-test section)

- `uv run pytest -q` on `dev/PRD-21626 @ 7e5d2c5`: 140 passed, 0 failed — matches the Self-test
  claim exactly.
- `uv run ruff check .`: 3 pre-existing errors, 0 new (see finding 3 for the file-attribution
  correction).
- `uv run ruff format --check .`: 5 files flagged, 1 new vs. base (finding 1).
- Chinese-text scan (`grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .`):
  no hits outside pre-existing `docs/tickets/PRD-2162*.md` files — matches the claim.
- Local server smoke test (`uv run python -m itglue_mcp` on 0.0.0.0:8080): `GET /health` → 200;
  `POST /mcp` `initialize` with no `X-ITGlue-API-Key` → 401; with a placeholder key,
  `initialize` → 200 then `tools/list` → 200 with 40 tools, `delete_attachment` present — matches
  the claim exactly.
- Code read: `delete_attachment` (`src/itglue_mcp/tools/attachments.py:86-105`) follows the exact
  same shape as its siblings `create_attachment`/`list_attachments` in the same file (same
  `ResourceType` literal, same `seg(resource_id)` path-segment guard, same `run()` wrapper) and the
  same destructive-delete body/return shape as `delete_document`
  (`src/itglue_mcp/tools/documents.py:269-283`), adapted to the relationship path
  (`/{resource_type}/{resource_id}/relationships/attachments`) the ticket actually asks for —
  matches the tech design's chosen option, no scope creep into a flexible-asset-only tool.
  `tests/test_handlers.py` new tests (6) each map 1:1 to an AC in `docs/tickets/PRD-21626.ac.json`
  and all pass.
- `tests/fixtures/tools_baseline.json`, `tests/test_middleware.py` (37→... corrected to 39→40,
  consistent with `main` having advanced past the design's stale baseline — confirmed by reading
  `ae5c844`'s actual live tool count), `README.md`'s Attachments row, `tests/test_tools.py`'s
  `destructive` tuple — all consistent with the Self-test's Change list and with each other.
- No scope creep: `git diff ae5c844...HEAD --stat` touches only the files the tech design's Change
  list and Self-test's Change list named (plus the two docs files). No change to
  `create_attachment`, `list_attachments`, or any other tool's behaviour.
- Credential handling: `delete_attachment` takes no new header, reuses `run()`/`current()`/
  `ITGlueClient` unchanged — no new credential path to audit.
- README Connector section (`README.md:13-82`, Agent Platform connector blurb) is byte-identical
  to `~/.claude/skills/vendor-mcp-development/reference/readme-connector-section.md` and untouched
  by this diff (only the Attachments row in the Tools table, outside that section, changed).

### Fixes

1. [must-fix, fixed] `tests/test_tools.py:36-42` — ran `uv run ruff format tests/test_tools.py`,
   which wrapped the `destructive` tuple one item per line exactly as the review's `--diff` output
   showed. No other change to the file or its assertions.
   Re-verified `uv run ruff format --check .`: 4 files flagged
   (`docs/tickets/PRD-21624.md`, `src/itglue_mcp/_json.py`, `tests/test_handlers.py`,
   `tests/test_paging_offset.py`) — the same 4 pre-existing files as the base (`ae5c844`), no new
   ones; `tests/test_tools.py` no longer appears.
   `uv run ruff check .`: 3 pre-existing errors, 0 new (unchanged from the review's own
   verification).
   `uv run pytest -q`: 140 passed, 0 failed — same as the review's independent run, no regressions.
   Local server smoke test (`uv run python -m itglue_mcp` on 0.0.0.0:8080): `GET /health` → 200;
   `initialize` with no `X-ITGlue-API-Key` → 401; with a placeholder key, `initialize` → 200,
   `tools/list` → 200 with 40 tools, `delete_attachment` present.
   Chinese-text scan: no hits outside the pre-existing `docs/tickets/PRD-2162*.md` files.

2. [suggestion, not addressed] `docs/changes/` entry for `delete_attachment` — out of scope for
   this round; the review marked it a suggestion, not a must-fix, and this round only touches the
   formatting of `tests/test_tools.py`. Left for a future pass or explicit instruction.

3. [suggestion, not addressed] `docs/tickets/PRD-21626.md` Self-test's `ruff check` file
   attribution — same as above, the main ticket doc is frozen and not reopened for a suggestion;
   the correction is recorded here in the review doc instead so a future reader has the accurate
   file list (`tests/test_handlers.py:5` `I001`, `tests/test_handlers.py:221` `E501`,
   `tests/test_passwords.py:5` `I001`).

Fixed on `dev/PRD-21626` — see `[DEV · PRD-21626] Review fixes round 1` stub for the commit sha.
