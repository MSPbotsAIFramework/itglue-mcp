# 2026-10-31 Create flexible asset type (PRD-21620)

Closes a Rewst -> MSPbots migration gap: the connector had tools to list, search, read, create
and update *flexible asset records*, but none to create the *type* itself first.

- `itglue_create_flexible_asset_type(name, enabled=None, description=None, icon=None, fields=None)` —
  creates a flexible asset type (`POST /flexible_asset_types`), optionally together with its field
  definitions in the same request (`data.relationships.flexible-asset-fields`). Each field needs
  `name` and `kind`; other per-field attributes (`order`, `required`, `show_in_list`,
  `use_for_title`, `tag_type`, `hint`, `default_value`) are optional and forwarded unvalidated —
  IT Glue rejects an invalid `kind` with `invalid_argument`. A field's `default_value` is masked
  from error messages, same posture as a trait value.
- `api.attributes()` gained an optional `relationships` parameter so a tool can build a compound
  JSON:API create document without a second body-building path; `None` (the default) preserves the
  previous output byte-for-byte.

No change to any existing tool's name, parameters or response shape. No live IT Glue account was
available to verify the relationships attribute casing end-to-end; the design treats the vendor's
own JSON:API convention (kebab-case attributes, confirmed against this repo's existing tests) as
authoritative over the ticket's own Rewst-sourced example body — see
`docs/tickets/PRD-21620.md`'s Open questions.
