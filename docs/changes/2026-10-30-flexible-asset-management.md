# 2026-10-30 Flexible asset management (PRD-21217)

Closes the one gap in the "configurations, passwords, runbooks, flexible assets" coverage: flexible
assets were read-only (`list_flexible_asset_types`, `search_flexible_assets`). Configurations,
passwords and runbooks (IT Glue Documents) were already fully covered.

- `get_flexible_asset(id)` — read one flexible asset by ID, including its trait values.
- `create_flexible_asset(organization_id, flexible_asset_type_id, name=None, traits=None)` — create a
  flexible asset of a given type under an organization.
- `update_flexible_asset(id, name=None, traits=None, archived=None)` — partial update; only the
  fields passed are sent. Rejects a call with no fields to change (`invalid_argument`), matching
  `update_password` / `update_location`. `archived` is exposed as a field on this tool rather than
  separate archive/unarchive tools: flexible assets never had a compatibility baseline requiring that
  split (unlike configurations/documents), and IT Glue's PATCH takes `archived` as one more attribute.
- Trait values are treated as opaque, account-specific custom data and are masked from error
  messages/logs the same way password secrets are, since no trait name is assumed safe by default.

No change to any existing tool's name, parameters or response shape.
