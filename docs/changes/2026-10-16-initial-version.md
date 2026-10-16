# 2026-10-16 Initial version

First release of the MSPbots IT Glue MCP server, written from the public IT Glue API documentation.

- 33 tools covering organizations, configurations, locations, passwords, documents, document
  sections and folders, attachments, flexible assets and user metrics.
- Tool names and parameters are compatible with the previous IT Glue connector on the platform.
  `create_document_section` gains an optional `level` for headings (default 2).
- Credentials: `X-ITGlue-API-Key` (required), `X-ITGlue-Region`, `X-ITGlue-Base-URL`
  (must be https on `*.itglue.com`).
- Behaviour differences from the previous connector:
  - No interactive folder picker: `create_document` without a folder creates the document at
    the organization root.
  - No JWT fallback for `list_document_folders`; the API key is used.
  - `page_size` is capped at 200 (was 1000); use `has_more` / `page_number` to page.
  - `search_documents` without a folder lists documents in all folders.
  - `list_flexible_asset_types` ignores `organization_id` (types are account-wide).
