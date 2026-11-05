# 2026-10-31 create_flexible_asset accepts archived and restricted (PRD-21621)

Closes a Rewst -> MSPbots migration gap: `create_flexible_asset` (added by PRD-21217) was missing
two of the vendor API's five create-time attributes.

- `create_flexible_asset(organization_id, flexible_asset_type_id, name=None, traits=None,
  archived=None, restricted=None)` — two new optional boolean parameters, folded into the request
  body only when passed (same convention `update_flexible_asset` already uses for `archived`).
  Neither parameter is required; omitting both leaves the request byte-for-byte unchanged from
  before this ticket.

No change to any other tool's name, parameters or response shape. No new dependency.
