# 2026-11-04 update_flexible_asset: organization_id and restricted (PRD-21622)

Closes a gap surfaced by the Rewst migration gap register (`it_glue.update_flexible_asset`): IT Glue's
`PATCH /flexible_assets/{id}` accepts `organization_id` and `restricted` alongside `name`, `traits`
and `archived`, but `update_flexible_asset` (added 2026-10-30 for PRD-21217) only exposed the latter
three.

- `update_flexible_asset(id, name=None, traits=None, archived=None, organization_id=None, restricted=None)`
  — two new optional parameters. Only non-`None` fields are sent, same as every other field on this
  tool; `restricted=False` is sent as `false`, not dropped (only `None` means "not provided").
- No new tool, no new required parameter, no change to any other tool's name, parameters or response
  shape. Backward compatible: a call that only passes the pre-existing fields produces byte-for-byte
  the same request as before this change.
- `tests/fixtures/tools_baseline.json`'s `update_flexible_asset` entry updated to list the two new
  optional params, so the compatibility baseline keeps reflecting what the tool actually accepts.
