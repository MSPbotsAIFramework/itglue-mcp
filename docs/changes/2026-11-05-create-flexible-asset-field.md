# 2026-11-05 Add a field to a flexible asset type (PRD-21627)

Closes a Rewst -> MSPbots migration gap (gap register item 64, Rewst action
`it_glue.create_flexible_asset_field`): the connector could create a flexible asset type with its
fields in one call (`itglue_create_flexible_asset_type`), but could not add a field to a type that
already exists.

- `itglue_create_flexible_asset_field(flexible_asset_type_id, name, kind, order?, required?,
  show_in_list?, use_for_title?, tag_type?, hint?, default_value?)` — posts to
  `POST /flexible_asset_types/{id}/relationships/flexible_asset_fields` and returns the new field
  (at least its `id`). Only the attributes passed are sent. `kind` and `tag_type` are forwarded
  unchanged; IT Glue validates them. `default_value` is masked from error messages and logs, same
  as in `itglue_create_flexible_asset_type`.

No change to any existing tool's name, parameters or response shape. No live IT Glue account was
available; the request shape follows the connector's other JSON:API create tools — see
`docs/tickets/PRD-21627.md`.
