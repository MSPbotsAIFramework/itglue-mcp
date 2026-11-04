# 2026-10-31 Get flexible asset type by ID (PRD-21624)

Closes a Rewst -> MSPbots migration gap: the connector could list flexible asset types and
search/read/create/update flexible asset *records*, but had no tool to read a single flexible
asset *type*'s own field (trait) definitions by ID.

- `get_flexible_asset_type(id)` — reads one flexible asset type
  (`GET /flexible_asset_types/{id}?include=flexible-asset-fields`) and returns its attributes plus
  a `fields` list, one entry per field IT Glue has defined for that type (id, name, kind and any
  other attributes IT Glue returns). `fields` is `[]`, not a missing key, when the type has no
  custom fields configured.
- `api.included()` is a new helper, a direct sibling of the existing `api.flatten()`/`api.item()`,
  that flattens a JSON:API response's `included` sideload array (optionally filtered by resource
  `type`). This is the first tool in the repo that reads `include=`/`included`; no other tool or
  helper changed.

No change to any existing tool's name, parameters or response shape. No live IT Glue account was
available to verify the exact attribute set IT Glue returns per field; the server does not rename
or drop attributes, so this only affects the precision of this doc's example, not correctness —
see `docs/tickets/PRD-21624.md`'s Risks section.
