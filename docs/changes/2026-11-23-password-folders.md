# 2026-11-23 Password folders (PRD-22427)

Lets an agent place password entries in an IT Glue password folder. All changes are additive:
new parameters are optional and calls that do not pass them behave as before.

- New tool `list_password_folders`: lists an organization's password folders (id, name, parent
  folder) from `GET /organizations/{id}/relationships/password_folders`, paged like the other list
  tools, with a local case-insensitive `name` match on the returned page.
- `create_password`: optional `password_folder_id`, sent as the `password-folder-id` attribute. If
  IT Glue's response does not show that folder, one follow-up `PATCH /passwords/{id}` moves the
  entry. If the move fails the created entry is returned with a `warning` (not an error) so a retry
  does not create a duplicate.
- `update_password`: optional `password_folder_id` moves an existing entry; it counts as a field
  for the "pass at least one field" check.
- `search_passwords`: optional `password_folder_id`, sent as `filter[password_folder_id]`.
- Whether IT Glue honours the folder on create/update is not confirmed against a live account.
