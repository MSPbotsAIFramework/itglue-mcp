# PRD-22427 · Code review

## Round 1 · 2026-11-23 · reviewed dev/PRD-22427 fa3aa65 (base b96db74)

Verdict: approved

### Findings
1. [suggestion] src/itglue_mcp/tools/passwords.py:177 — The create-then-move fallback depends on IT Glue behaviour that is not yet verified against a real account (TC-ITGPF-009 is blocked for lack of credentials). Code handles both outcomes and is covered by mocked tests; confirm on INT with a real organization.
2. [suggestion] src/itglue_mcp/tools/passwords.py:111 — The `name` filter in list_password_folders applies only to the returned page; this is stated in the parameter description, acceptable.

Checks: diff scope matches the tech design (passwords.py, tests, tools baseline, README tools row, change note); credentials are not logged (secrets passed to run()); `uv run pytest -q` re-run on the branch HEAD: 170 passed; no CJK characters in code, tests, README or change note; self-test evidence matches HEAD fa3aa65; main has not moved since the sync (b96db74).

Status: frozen @ fa3aa65
