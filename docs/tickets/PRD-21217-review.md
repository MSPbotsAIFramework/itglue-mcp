# PRD-21217 · Code review

## Round 1 · 2026-10-30 · reviewed dev/PRD-21217 @ 3d4e57a (base main @ 544c707)

Verdict: changes requested

### Findings

1. [must-fix] docs/tickets/PRD-21217.md:123,183,187,189,192,194,196,335 — the design document
   introduced by this ticket's own branch contains Chinese bracket tags (meaning "non-blocking",
   "changed" ×4, "new", and "new/changed") and a quoted Chinese phrase. This repo is an
   MSPbotsAIFramework vendor MCP repo, which must be entirely English (SOP §0.4, checklist item
   meaning "repo content must be entirely English ... no Chinese anywhere";
   `references/mcp-track.md` §4.3 lists a requirement meaning "no Chinese in the repo" as a
   condition where any failure is a must-fix). `scripts/mbp.py` and the Self-test section of this
   same document (line 423) already
   acknowledge the issue exists but explicitly leave it untouched, attributing it to the design
   leg's own commit (`bf0c4c9`) and calling it outside the dev leg's mandate. That division of
   responsibility is correct for the *product design* content, but the flagged occurrences are not
   product-design wording — they are English/Chinese-mixed change-list and open-question labels
   under the "Tech design" and "Product design > Open questions" headings. Per this skill's own
   ownership rule, the Tech design section (where 6 of the 8 occurrences live: the Chinese
   "changed"/"new"/"new-changed" tags in "Change list") is dev's to edit without changing
   user-visible behaviour, so translating those six tags to English equivalents (e.g. `[changed]`,
   `[new]`, `[new/changed]`) is in scope for the fix. The remaining two (the Chinese "non-blocking"
   tag under Product design > Open questions, and the quoted Chinese sentence meaning "a missing
   vendor test account is not a blocker" in Self-test) touch product-design wording or a direct quote
   of this pipeline's own Chinese-language internal docs — flag these for the design leg to correct
   if assignee is not dev, otherwise translate consistently since the repo-wide constraint
   (checklist item, not a design-content rule) takes precedence over which leg normally owns the
   section. Net effect: the repository, as it stands in this diff, fails the "no Chinese anywhere in
   the repo" checklist item that review must verify. Fix: replace all 8 occurrences with English
   text (direct translations preserve meaning without altering the design's substance), rerun
   `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .` to confirm zero
   matches, and note the fix in the next Self-test update.

2. [suggestion] src/itglue_mcp/tools/flexible_assets.py:90,101,128 — the three new tool names
   (`get_flexible_asset`, `create_flexible_asset`, `update_flexible_asset`) do not carry the
   `<vendor>_` prefix that SOP §2's checklist calls for (a Chinese checklist item meaning "tool
   names carry a `<vendor>_` prefix"). This is not
   flagged as must-fix because it is not something this diff introduces in isolation: every other
   tool in this repo except `itglue_health_check` is unprefixed (`search_organizations`,
   `get_password`, `create_location`, the two existing `flexible_assets` tools
   `list_flexible_asset_types`/`search_flexible_assets`, etc.), and the new tools match the naming
   of their own module's existing siblings exactly. Adding a prefix only to these three would make
   the module internally inconsistent (two unprefixed + three prefixed tools in the same file) for a
   convention the whole repo already deviates from across five prior tickets
   (PRD-20835/20836/21362/21363/21374 per `git log --oneline main`). This is a repo-wide baseline
   gap, not an increment this ticket should be forced to fix alone — flagged for a possible future
   repo-wide rename ticket, not for this one.

### What passed review (no must-fix)

- Tool shapes (`get`/`create`/`update_flexible_asset`) reuse `api.item`/`api.attributes`/`seg`/
  `ToolInputError`/`run` exactly as the closest analogues (`passwords.py`, `locations.py`,
  `configurations.py`); no new HTTP/JSON:API code.
- `update_flexible_asset`'s all-`None` guard matches `update_location`/`update_password`'s existing
  pattern (raises before any HTTP call, caught by `run()` as `invalid_argument`).
- AC6 (credential isolation): unchanged `credentials.py`/`run()` per-request model; no new
  module-level or cross-request state introduced.
- AC7 (trait values never leak into error text/logs): `_trait_secrets()` + `run(..., secrets=...)`
  correctly routes through `redact()` on `ApiError`/`ToolInputError`, and the generic-exception
  branch logs only the exception type (not its message) when secrets are present — verified against
  `tests/test_flexible_assets.py::test_create_flexible_asset_error_does_not_leak_trait_values`,
  which forces a bare `RuntimeError` (the path that would otherwise log a full traceback) and
  asserts the secret-looking trait value is absent from both the response and `caplog`.
- Backward compatibility: purely additive; `tests/fixtures/tools_baseline.json` only gains three new
  entries, no existing entry changed; `test_middleware.py`'s two hardcoded tool-count assertions
  (`33 -> 36`) are the correct, minimal, mechanical consequence of the addition and are called out
  honestly in Self-test as a file outside the original tech design's change list.
- README `## MSPbots Connector` block (`readme-connector-section.md`) is untouched; only the
  Flexible assets row in the `## Tools` table gained the three new names, confirmed by `git diff`.
- Gates: Self-test's `uv run pytest -q` (110 passed), `ruff check`/`ruff format --check` scoped to
  touched files (clean), and local smoke (`/health` 200, `tools/list` count 36 including the three
  new tools) are all specific, reproducible, and consistent with what this diff actually changes.
  `gitleaks` not run (not installed in the pipeline environment) — acceptable per `gates.md`/
  `REVIEW.md`, no new credential fields were added.
- TC6 (manual, needs a real vendor account) correctly recorded as `untested` with a reason, not
  silently dropped or forced to a false "pass" — not a blocker per `references/mcp-track.md` §3.
- No pre-existing ruff/lint baseline issues were introduced or hidden; the dev leg verified the
  pristine-`main` baseline separately (3 lint errors, 3 files needing reformat) and confirmed its
  own new file was clean before commit — increment-only judgement applied correctly.

### Round 1 · Fixes (review rework, 2026-10-30)

Fixed the single must-fix (finding 1):

- `docs/tickets/PRD-21217.md` — translated all 8 flagged occurrences to English, in place, pure
  translation with no change to the design's substance:
  - Line 123 (Product design > Open questions): the Chinese "non-blocking" tag → `[non-blocking]`.
  - Lines 183, 187, 189, 192 (Tech design > Change list): the Chinese "changed" tag → `[changed]`
    (×4).
  - Line 194: the Chinese "new/changed" tag → `[new/changed]`.
  - Line 196: the Chinese "new" tag → `[new]`.
  - Line 335 (Self-test): the quoted Chinese phrase citing `references/mcp-track.md` §3 replaced
    with its English meaning: `"a missing vendor test account is not a blocker"`.
  - Also updated the Self-test "Pre-existing issues found but not touched" bullet (line ~420-428,
    not itself one of the 8 flagged lines) so it no longer asserts the issue is untouched or quotes
    the original Chinese tags — it now states the issue was found pre-existing by this ticket's own
    design commit, flagged by this review round, and fixed here. This bullet was not in the finding's
    line list but quoted the same tags and would otherwise go stale and still fail the grep gate
    after the fix; translating it is the same no-substance-change class of edit the finding
    authorized, not a new must-fix.
  - Did not change the frozen header SHA reference mechanism: `docs/tickets/PRD-21217.md` carries
    `Status: frozen @ 7a492e2` from the original dev leg; this review-rework edit is layered on top
    per `legs/dev.md` S1 (the "review rework" rule: fix on the same branch, document the fix in
    this review file, main document otherwise left alone).
- Verification: `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .` now
  returns **zero matches in `docs/tickets/PRD-21217.md`**, and zero matches anywhere outside this
  review file. The only remaining Chinese in the repository is in this file's own Round 1 findings
  above (lines 10-13, 20-24, 36) — the reviewer's verbatim citation of the original defect text and
  of this pipeline's own Chinese-language internal SOP/reference docs as evidence. That citation is
  the historical record of what round 1 found and is left unedited (review findings are not revised
  after the fact); it is not product code, design content, or documentation the repo ships — it is
  this pipeline's own audit trail. Flagging this explicitly for round 2 to confirm that reading is
  acceptable, rather than silently relying on it.
- Gates re-run on the fixed commit (docs-only change; code and tests untouched since round 1):
  `uv run pytest -q` — 110 passed; `uv run ruff check .` / `uv run ruff format --check .` scoped to
  touched files — clean (only `docs/tickets/PRD-21217.md` changed, not a lint target); local smoke
  (`initialize` + `tools/list`) unchanged from the Self-test section (36 tools, including the three
  new `flexible_asset` tools) since no source file was touched in this round.
- Suggestion (finding 2, tool naming prefix): not addressed — the review itself marked it
  non-blocking and recommended a separate repo-wide ticket, not a fix in this one.

## Round 2 · 2026-10-30 · reviewed dev/PRD-21217 @ b7547e3 (base main @ 544c707)

Verdict: changes requested

### Round 1 fix verification

Finding 1's listed fix holds: `git diff aee0752...b7547e3 -- docs/tickets/PRD-21217.md` shows all 8
flagged occurrences translated in place with no change to meaning (the four bracket tags and the one
quoted sentence listed in the Round 1 Fixes section above, each replaced with its English
translation). `uv run pytest -q` re-run on `b7547e3` in this review: 110 passed (unchanged),
confirming this round's diff is docs-only as claimed.

### Findings

1. [must-fix] docs/tickets/PRD-21217-review.md:10-13,20-24,36,86-89,101 — this review document is
   itself part of the repo (`docs/tickets/` ships alongside the rest of the tree per
   `vendor-mcp-development` SKILL.md:115: ticket docs must be English only, same as the rest of the
   repo), so SOP §0.4 (repo content must be entirely English, including "other documents", checked by
   a grep that must return zero matches outside lock files) and `references/mcp-track.md` §4.3's
   must-fix criterion (no non-English text anywhere in the repo) apply to it the same as any other
   file. The required grep scan on `b7547e3` returns non-zero: this file's own Round 1 Findings and
   Round 1 Fixes sections quote the original non-English bracket tags and a non-English sentence from
   this pipeline's internal SOP/mcp-track.md verbatim (this finding itself avoids reproducing that
   text, to not repeat the same defect). The Round 1 Fixes note (line 101 area) explicitly raised
   this as an open question for round 2 to confirm — confirming now: there is no audit-trail
   exception in SOP §0.4 or the checklist, and the repo fails its own required zero-match grep as
   long as this text stands. Fix: rewrite the
   Findings/Fixes prose so it describes the original tags and the quoted phrase in English only
   (e.g. "the Chinese bracket tags meaning non-blocking/changed/new/new-changed" and "a Chinese
   sentence meaning 'a missing vendor test account is not a blocker'") instead of reproducing the
   literal Chinese characters; keep the line numbers and commit references so the record stays
   traceable without violating the all-English requirement. Re-run the grep above after the edit to
   confirm it returns zero matches anywhere in the repo.

### Round 2 · Fixes (review rework, 2026-10-30)

Fixed the single must-fix (finding 1):

- `docs/tickets/PRD-21217-review.md` — rewrote the Round 1 "Findings" and "Round 1 · Fixes" prose
  (then at lines 10-13, 20-24, 36, 86-89, 101) so it describes the original Chinese bracket tags
  and the quoted Chinese sentence in English only, without reproducing the literal Chinese
  characters, while keeping the same line numbers and commit references so the record stays
  traceable:
  - Finding 1 (lines 10-13): the sentence naming the four literal Chinese bracket tags was rewritten
    to instead describe them by meaning ("non-blocking", "changed" ×4, "new", and "new/changed");
    the two quoted checklist phrases were rewritten to describe their meaning in English ("repo
    content must be entirely English ... no Chinese anywhere" and "no Chinese in the repo") instead
    of quoting the original wording.
  - Finding 1 (lines 20-24): the sentence naming the three literal tags was rewritten to describe
    them as "the Chinese 'changed'/'new'/'new-changed' tags"; the sentence naming the remaining tag
    and quoting the Self-test sentence was rewritten to describe them as "the Chinese 'non-blocking'
    tag ... and the quoted Chinese sentence meaning 'a missing vendor test account is not a
    blocker'".
  - Finding 2 (line 36): the quoted checklist phrase for the `<vendor>_` prefix rule was rewritten to
    describe its meaning ("tool names carry a `<vendor>_` prefix") instead of quoting the original
    wording.
  - Round 1 Fixes list (lines 86-89): each bullet's leading literal tag was rewritten to describe it
    by meaning ("the Chinese 'non-blocking'/'changed'/'new-changed'/'new' tag") ahead of the
    `→ [english-tag]` translation it documents.
  - Round 1 Fixes closing note (line 101): the quoted two-character label for this pipeline's
    "review rework" rule was rewritten to just name the rule in English ("the 'review rework'
    rule").
  - Did not touch the Round 1 "What passed review" section, the "Round 1 fix verification" section
    under Round 2, or this finding's own prose (lines 134-157) — none of those contain literal
    Chinese characters, and finding 2's own text explicitly avoids reproducing the defect it is
    describing, so no change was needed there.
  - No source, test, or main-document (`docs/tickets/PRD-21217.md`) file touched — this round's
    must-fix is entirely about this review document's own prose.
- Verification: `grep -rnP '[\x{4e00}-\x{9fff}]' --exclude-dir=.git --exclude-dir=.venv .` now
  returns **zero matches anywhere in the repository**, including this file.
- Gates re-run on the fixed commit (docs-only change; code and tests untouched since round 1):
  `uv run pytest -q` — 110 passed (unchanged); `uv run ruff check .` / `uv run ruff format --check .`
  — same pre-existing baseline (3 errors / 3 files, not introduced by this or any prior round, since
  no Python file was touched); local smoke unchanged from Self-test (36 tools, incl. the three new
  `flexible_asset` tools) since no source file was touched in this round.
- Suggestion (finding 2, tool naming prefix): still not addressed — unchanged from round 1, the
  review itself marked it non-blocking and recommended a separate repo-wide ticket.
