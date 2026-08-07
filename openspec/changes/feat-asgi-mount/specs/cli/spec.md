# Delta Spec: cli

## ADDED Requirements

### Requirement: The server shall mount user-provided ASGI applications
The dev/prod server SHALL support mounting user-provided ASGI applications at configured path prefixes. Mounts SHALL be declared via `WebComPyServerConfig.mounts`, a zero-argument callable returning `dict[str, ASGIApp]` (path prefix → ASGI app) or `None`. `create_asgi_app()` SHALL invoke the callable at most once per serving app construction and SHALL insert one Starlette `Mount` per entry into the route list immediately before the SSR catch-all route (`/{path:path}`), after all framework-internal and static-file routes. Mount path prefixes SHALL NOT be prefixed by `app.base_url`.

#### Scenario: Mounting a FastAPI app at /api
- **WHEN** `WebComPyServerConfig(mounts=lambda: {"/api": fastapi_app})` is configured and the server is running
- **THEN** a request to `/api/users` SHALL be handled by `fastapi_app`
- **AND** a request to a page route SHALL still be handled by SSR

#### Scenario: Mounts take precedence over the catch-all
- **WHEN** a mount is configured at `/api` and no page route matches `/api/anything`
- **THEN** requests to `/api/...` SHALL be routed to the mounted app, not to SSR
- **AND** unmatched paths inside the mount SHALL produce the mounted app's own 404

#### Scenario: No mounts configured preserves current behavior
- **WHEN** `mounts` is `None` (default)
- **THEN** the route table SHALL be exactly as before this change

### Requirement: Mount path collisions shall fail fast at startup
`create_asgi_app()` SHALL validate mount prefixes before constructing the ASGI app. A mount prefix that starts with `/_webcompy` (framework-reserved) SHALL be rejected. A mount prefix that collides with a registered page route SHALL be rejected. On any collision, the server SHALL raise an error listing all conflicting paths before serving begins; the same validation SHALL apply during SSG.

#### Scenario: Reserved prefix collision
- **WHEN** a mount is declared at `/_webcompy-api`
- **THEN** startup SHALL fail with an error naming `/_webcompy-api` as reserved

#### Scenario: Page route collision
- **WHEN** a page route `/admin` exists and a mount is declared at `/admin`
- **THEN** startup SHALL fail with an error listing the conflict
