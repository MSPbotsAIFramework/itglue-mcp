# IT Glue MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets AI agents on the
MSPbots Agent Platform read and update IT Glue documentation: organizations, configurations,
locations, passwords, documents, flexible assets, attachments and user activity metrics.

It runs as a stateless HTTP service behind the MSPbots MCP gateway. The gateway sends each
tenant's IT Glue credentials as request headers on every call; the server keeps nothing between
requests.

## Credentials (request headers)

| Header | Required | Meaning |
|---|---|---|
| `X-ITGlue-API-Key` | Yes | IT Glue API key. Create it in IT Glue under **Account > Settings > API Keys** (Administrator role required). Enable password access on the key if agents should read or write passwords. |
| `X-ITGlue-Region` | No | Data center: `us` (default), `eu` or `au`. |
| `X-ITGlue-Base-URL` | No | Custom API endpoint. Must be `https://` on an `*.itglue.com` host. Takes precedence over the region. |

Header names are case-insensitive. A request to `/mcp` without an API key gets `401` with the list
of expected headers; an invalid region or base URL gets `400`.

Note: IT Glue revokes API keys that have not been used for 90 days.

## Tools

| Area | Tools |
|---|---|
| Organizations | `search_organizations`, `get_organization` |
| Configurations | `search_configurations`, `get_configuration`, `archive_configuration`, `unarchive_configuration` |
| Locations | `search_locations`, `get_location`, `create_location`, `update_location` |
| Passwords | `search_passwords`, `get_password`, `create_password`, `update_password` |
| Documents | `search_documents`, `get_document`, `list_document_folders`, `create_document`, `update_document`, `delete_document`, `publish_document`, `archive_document`, `unarchive_document` |
| Document sections | `list_document_sections`, `create_document_section`, `update_document_section`, `delete_document_section` |
| Attachments | `create_attachment`, `list_attachments` |
| Flexible assets | `list_flexible_asset_types`, `search_flexible_assets` |
| Activity | `search_user_metrics` |
| Diagnostics | `itglue_health_check` |

Tool names and parameters match the previous IT Glue connector on the MSPbots Agent Platform, so
existing agents keep working. This is why the server has more than 20 tools and why most names
have no `itglue_` prefix.

Behaviour notes:

- Every tool returns a JSON string. Errors use one envelope:
  `{"error": {"code": "...", "message": "...", "retryable": false}}` with `code` one of
  `not_configured`, `unauthorized`, `not_found`, `invalid_argument`, `rate_limited`, `upstream_error`.
- List tools return `{"items", "count", "page_number", "page_size", "has_more", "total_count"}`.
  `page_size` defaults to 50 and is capped at 200. Results larger than 20,000 characters are cut
  and flagged with `truncated` / `has_more`.
- `search_passwords` never returns secrets. `create_password` and `update_password` do not echo them.
- IT Glue has no server-side name filter for documents or folders and no username filter for
  passwords; those filters are applied to the returned page.
- Section edits are only visible after `publish_document`.
- Transient failures (429, 5xx, timeouts) are retried with backoff, honouring `Retry-After`.

## Run locally

```bash
uv sync
uv run itglue-mcp            # listens on 0.0.0.0:8080
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H "X-ITGlue-API-Key: $ITGLUE_API_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Environment variables (all optional): `MCP_HTTP_HOST` (default `0.0.0.0`), `MCP_HTTP_PORT`
(default `8080`), `MCP_TRANSPORT` (`http` or `stdio`). Unknown variables are ignored. Credentials
are never read from the environment.

## Docker

```bash
docker build -t itglue-mcp .
docker run --rm -p 8080:8080 itglue-mcp
```

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check .
```

Code is in `src/itglue_mcp/` (one module per area under `tools/`), tests in `tests/`.
The implementation follows the public IT Glue API documentation at https://api.itglue.com/developer/.

## License

Copyright 2026 MSPbots.ai. Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE)
and [NOTICE](NOTICE).

IT Glue is a trademark of its owner. This project is not affiliated with or endorsed by IT Glue.
