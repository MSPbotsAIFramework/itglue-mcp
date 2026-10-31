# 2026-10-31 List account users (PRD-21586)

Closes a Rewst -> MSPbots migration gap: the connector had no tool that reads the IT Glue
account's own user directory (`search_user_metrics` reads per-user *activity* counts, not the
directory).

- `itglue_list_account_users(name=None, email=None, role_name=None, sort=None, page_size=None, page_number=None, offset=None)` —
  read-only, lists the account's users (`GET /users`) with `id`, `first_name`, `last_name`,
  `email`, `role_name`, `my_glue`, `last_sign_in_at` and the other attributes IT Glue returns.
  Filters and paging work the same as every other list tool in this connector. IT Glue's
  `filter[name]` on `/users` is an exact match, unlike the fuzzy-feeling name filters elsewhere.

No change to any existing tool's name, parameters or response shape.
