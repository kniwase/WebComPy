# Delta Spec: server-fetch-asgi

## MODIFIED Requirements

### Requirement: ServerFetchPort shall resolve self-site URLs against base_url

When `base_url` is configured on the app (e.g., `/myapp/`), self-site absolute paths SHALL be resolved with the `base_url` prefix, EXCEPT for paths under a configured ASGI mount prefix: mounts are absolute server paths, so paths under a mount prefix SHALL be dispatched without the `base_url` prefix. For example, with `base_url="/myapp/"`, a fetch to `/api/data` SHALL be routed to `/myapp/api/data` unless `/api` is a configured mount, in which case it SHALL be dispatched as `/api/data`.

#### Scenario: Self-site fetch with base_url
- **WHEN** `base_url="/myapp/"` is configured
- **AND** a component calls `await fetch_port.fetch("/api/data")`
- **AND** `/api` is NOT a configured mount
- **THEN** the request SHALL be routed to `/myapp/api/data` within the ASGI app

#### Scenario: Self-site fetch with default base_url
- **WHEN** `base_url="/"` is the default
- **AND** a component calls `await fetch_port.fetch("/api/data")`
- **THEN** the request SHALL be routed to `/api/data` within the ASGI app

#### Scenario: Self-site fetch to a mount path under non-root base_url
- **WHEN** `base_url="/myapp/"` is configured and `/api` is a configured mount
- **AND** a component calls `await fetch_port.fetch("/api/users")`
- **THEN** the request SHALL be dispatched as `/api/users` (without the `base_url` prefix)
- **AND** the request SHALL reach the mounted app in-process via `httpx.ASGITransport`

## ADDED Requirements

### Requirement: Mount path prefixes shall not be blocked for self-site fetch
`blocked_paths` derivation SHALL remain based on page routes only. Paths under a configured ASGI mount prefix SHALL NOT be considered blocked, even if a mounted endpoint shares a path shape with a page route. Self-site fetches to mount paths during SSR/SSG SHALL be routed through the ASGI transport and reach the mounted app in-process, dispatched without `base_url` prefixing per the base_url-resolution requirement.

#### Scenario: Fetching a mounted endpoint during SSR
- **WHEN** a component fetches `/api/users` during SSR and `/api` is a configured mount
- **THEN** the request SHALL be dispatched in-process via `httpx.ASGITransport` to the mounted app
- **AND** the response SHALL be returned to the component and recorded in the transfer cache as with any self-site fetch

#### Scenario: Mount paths never appear in blocked_paths
- **WHEN** `blocked_paths` is computed for an app with page routes and a `/api` mount
- **THEN** no entry in `blocked_paths` SHALL match `/api/...`
