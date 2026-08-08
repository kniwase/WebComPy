# Spec: asgi-embed

## ADDED Requirements

### Requirement: WebComPy serving apps shall be embeddable into host ASGI applications
The framework SHALL officially support embedding a WebComPy serving app into a host ASGI application via standard mounting (e.g. Starlette/FastAPI `Mount`/`mount`). The documented pattern is: construct the serving app with `create_asgi_app()`, wire the fetch port with `configure_server_context(app, root_app=host)`, and mount `serving.asgi` under a path prefix. In embedded mode the host application owns the server process (`run_server()` is not used). SSR pages, framework asset endpoints, and static files SHALL be served correctly under the mount prefix.

#### Scenario: Embedded SSR page render
- **WHEN** a WebComPy app is mounted at `/admin` in a host FastAPI app and a client requests `/admin/` (or a page path under it)
- **THEN** the SSR HTML SHALL be returned with correct asset URLs under `/admin`

#### Scenario: Framework endpoints work under the prefix
- **WHEN** a client requests `/_webcompy-assets/...` or other framework endpoints under the mount prefix
- **THEN** they SHALL be served as in standalone mode

#### Scenario: Resource endpoint works under the prefix
- **WHEN** a client requests `{mount_prefix}/_webcompy-resource/{path}` for an allow-listed resource
- **THEN** the resource SHALL be served as in standalone mode
- **AND** the standalone (non-embedded) resource-route behavior SHALL remain unchanged

#### Scenario: Host routes unaffected
- **WHEN** the host app has its own routes (e.g. `/api/items`)
- **THEN** direct requests to those routes SHALL be handled by the host exactly as if WebComPy were not mounted

### Requirement: base_url shall match the mount prefix in embedded mode
When embedded under a mount prefix, `AppConfig.base_url` SHALL be set to that prefix (e.g. `/admin/`). Generated asset URLs, router links, and self-site fetch URL resolution SHALL then align with the embedded location. The documentation SHALL present `base_url` and the mount prefix as a required pairing.

#### Scenario: Asset URLs carry the prefix
- **WHEN** `base_url="/admin/"` and the app is mounted at `/admin`
- **THEN** URLs emitted into the HTML for scripts/assets SHALL begin with `/admin/`

#### Scenario: Client-side navigation builds prefixed history URLs
- **WHEN** an embedded history-mode app with `base_url="/admin/"` performs a client-side navigation to `/users`
- **THEN** the browser history URL SHALL be built with the prefix via `HistoryPort` URL updates (`/admin/users/`)
- **AND** guard-driven redirects SHALL likewise replace URLs under the prefix

### Requirement: Self-site fetch in embedded mode shall reach the host application
When `configure_server_context(app, root_app=host)` is used, `ServerFetchPort` SHALL dispatch self-site fetches against the host ASGI application, so fetches from embedded components can reach the host's own routes (including sibling mounts and host API endpoints) in-process during SSR. Fetched responses SHALL be recorded in the hydration transfer cache as usual.

#### Scenario: Component fetches a host API during SSR
- **WHEN** an embedded component fetches `/api/items` during SSR and `/api/items` is a host route outside the WebComPy mount
- **THEN** the request SHALL be dispatched in-process through the host app via ASGI transport
- **AND** the response SHALL be returned to the component and recorded in the transfer cache

### Requirement: Blocked paths in embedded mode shall cover prefixed page routes only
In embedded mode, page-route blocking SHALL apply to WebComPy page paths under the mount prefix (e.g. `/admin/users`), preventing recursive SSR fetches. Host routes outside the mount prefix SHALL NOT be blocked.

#### Scenario: Page recursion still prevented
- **WHEN** an embedded component attempts a self-site fetch to `/admin/users` where `/users` is a WebComPy page route
- **THEN** the fetch SHALL be blocked with the standard blocked-path behavior

#### Scenario: Host API routes are not blocked
- **WHEN** an embedded component fetches `/api/items` (a host route)
- **THEN** the fetch SHALL NOT be blocked
