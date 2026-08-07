# Delta Spec: ssg-via-ssr

## ADDED Requirements

### Requirement: SSG shall remain functional when ASGI mounts are configured
`generate_static_site()` SHALL work unchanged when `WebComPyServerConfig.mounts` is set: the same `create_asgi_app(mode="prod")` pipeline SHALL be used, mount endpoints SHALL be reachable via `httpx.ASGITransport` during generation (so components can fetch mounted APIs in-process at build time), and only page routes plus the 404 page SHALL be written to `dist/`. Mount endpoint responses SHALL NOT be exported as static files. Responses fetched from mounts during generation SHALL be baked into hydration payloads via the existing transfer cache.

#### Scenario: Component fetches a mounted API during generation
- **WHEN** a page component fetches `/api/users` during SSG and `/api` is a configured mount
- **THEN** the fetch SHALL be served in-process via ASGITransport
- **AND** the response SHALL be included in the page's hydration transfer payload
- **AND** no `/api/...` file SHALL appear in `dist/`

#### Scenario: Static output contains only pages
- **WHEN** SSG completes for an app with mounts configured
- **THEN** `dist/` SHALL contain page HTML, static files, and framework assets only
