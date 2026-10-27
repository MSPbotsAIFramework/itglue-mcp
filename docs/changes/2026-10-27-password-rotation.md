# 2026-10-27 Password rotation (PRD-21374)

Finding an existing password entry and changing its secret is covered by the existing tools;
this change closes the remaining gaps. No tool was added or renamed.

- `update_password`: `organization_id` is now optional (was required). Without it the entry is
  updated through `PATCH /passwords/{id}`; with it through the organization route as before.
  The request sends `show_password=false`, and the response still drops `password` / `otp_secret`.
  Only supplied fields are sent (unchanged behaviour, now covered by tests).
- `search_passwords`: the local `username` filter now continues correctly across pages and cut
  results (`next_offset`), like the document name filters. The description names the fields to
  expect (id, name, username, category, updated_at).
- `create_password` / `update_password`: the `password` parameter is marked secret in the input
  schema (`format: password`, `writeOnly: true`) so callers and run records can mask it. The
  secret is masked in error messages, and unexpected errors are logged without a traceback when a
  secret was passed.
