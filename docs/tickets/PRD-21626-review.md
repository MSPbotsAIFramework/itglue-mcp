# PRD-21626 · Code review

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

### Fixes            ← appended by the dev leg on rework
