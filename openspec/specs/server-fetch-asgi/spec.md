# Server Fetch ASGI

## Purpose

Enable WebComPy components to fetch data from their own application's API endpoints during server-side rendering (SSR) and static site generation (SSG). Self-site requests are routed through the app's own ASGI app via `httpx.ASGITransport`, eliminating network I/O and enabling data fetching without a running server. Page routes that return HTML are blocked with a 500 status to prevent infinite recursion during rendering.

## Requirements

### Requirement: FetchPort shall classify URLs as self-site or external

`FetchPort` SHALL provide a non-abstract `is_self_site_url(url)` method with a default implementation returning `False`. This ensures backward compatibility with existing `FetchPort` implementations (including `BrowserFetchPort` and custom ports) that don't need self-site routing. URLs starting with `/` (absolute path) or `.` (relative path) SHALL be classified as self-site. All other URLs SHALL be classified as external.

Relative URLs starting with `.` SHALL be resolved against `base_url` root, not the current route path. For example, with `base_url="/myapp/"`, a fetch to `./api/data` resolves to `/myapp/api/data`. This is deliberately non-standard — standard RFC 3986 relative URL resolution would resolve `./api/data` against the current route path (e.g., from `/myapp/users/42` to `/myapp/users/api/data`). WebComPy overrides this because SSG/SSR has no concept of a "current route" during rendering. Developers who need route-relative resolution SHALL use absolute paths starting with `/`.

#### Scenario: Classifying an absolute path URL
- **WHEN** `fetch_port.is_self_site_url("/api/users")` is called
- **THEN** the result SHALL be `True`

#### Scenario: Classifying a relative path URL
- **WHEN** `fetch_port.is_self_site_url("./data")` is called
- **THEN** the result SHALL be `True`

#### Scenario: Classifying an external HTTPS URL
- **WHEN** `fetch_port.is_self_site_url("https://api.example.com/data")` is called
- **THEN** the result SHALL be `False`

#### Scenario: Classifying an external HTTP URL
- **WHEN** `fetch_port.is_self_site_url("http://localhost:3000/api")` is called
- **THEN** the result SHALL be `False`

### Requirement: ServerFetchPort shall support lazy ASGI app configuration

`ServerFetchPort` SHALL provide a `configure(asgi_app, blocked_paths)` method for lazy initialization. This method SHALL be called after the ASGI app is created, resolving the chicken-and-egg problem where `ServerFetchPort` is instantiated in `WebComPyApp.__init__()` before the ASGI app exists.

#### Scenario: Configuring ServerFetchPort with an ASGI app
- **WHEN** `server_fetch_port.configure(asgi_app, blocked_paths=["/"])` is called
- **THEN** self-site requests SHALL be routed through `httpx.ASGITransport` wrapping `asgi_app`
- **AND** external requests SHALL continue to use the normal httpx client

#### Scenario: Calling configure() multiple times
- **WHEN** `configure()` is called more than once on the same `ServerFetchPort` instance
- **THEN** the second call SHALL raise a `WebComPyException` indicating the fetch port is already configured
- **AND** no state change SHALL occur (the original ASGI app and blocked paths SHALL remain in effect)

#### Scenario: Self-site fetch before configuration
- **WHEN** `server_fetch_port.fetch("/api/data")` is called before `configure()` has been called
- **THEN** the fetch SHALL return a `Response` with `status_code=500` and an error message indicating the fetch port is not configured

### Requirement: ServerFetchPort shall route self-site requests through ASGI transport

Self-site requests SHALL be routed through `httpx.ASGITransport` wrapping the app's own ASGI app. This eliminates network I/O for same-application requests and enables data fetching during SSG without a running server.

#### Scenario: Fetching a self-site API endpoint
- **WHEN** a component calls `await fetch_port.fetch("/api/users")` during SSR
- **AND** the fetch port is configured with the app's ASGI app
- **THEN** the request SHALL be handled internally by the ASGI app
- **AND** no actual HTTP connection SHALL be made
- **AND** the `Response` SHALL contain the API endpoint's data

#### Scenario: Fetching an external URL
- **WHEN** a component calls `await fetch_port.fetch("https://api.example.com/data")` during SSR
- **THEN** the request SHALL be made via the external httpx client
- **AND** the request SHALL go through the normal network stack

### Requirement: ServerFetchPort shall block page routes during SSR

Page routes (routes that have a corresponding `Component` registered via `app.routes`) SHALL be blocked during self-site fetch to prevent infinite recursion. Blocked paths SHALL be derived from `app.routes` — any route tuple `(path, page_component, *_rest)` where `page_component` is not `None` SHALL be considered a page route. If a route has dynamic segments (e.g., `/users/:id`) and the path parameters are available (e.g., during SSG where all routes are enumerated), the dynamic segments SHALL be substituted with concrete values to produce the actual path (e.g., `/users/42`). If path parameters are not available (e.g., during dev server startup where route enumeration may not be possible), the literal route pattern string (e.g., `/users/:id`) SHALL be added to the blocked paths set — the `ServerFetchPort` SHALL then perform a prefix check against blocked patterns in addition to exact path matching to catch dynamic segment variations. When a blocked path is requested, `ServerFetchPort` SHALL return a `Response` with `status_code=500` and a descriptive error message.

#### Scenario: Fetching a blocked page route
- **WHEN** a component calls `await fetch_port.fetch("/")` during SSR
- **AND** `"/"` is in the blocked paths list
- **THEN** the fetch SHALL return a `Response` with `status_code=500`
- **AND** `ok` SHALL be `False`
- **AND** the response text SHALL indicate that the path is blocked during server-side rendering

#### Scenario: Fetching an API route that is not blocked
- **WHEN** a component calls `await fetch_port.fetch("/api/users")` during SSR
- **AND** `"/api/users"` is not in the blocked paths list
- **THEN** the fetch SHALL proceed through the ASGI app normally
- **AND** the response SHALL contain the API endpoint's data

#### Scenario: Dynamic route blocks all concrete paths via prefix matching
- **WHEN** the blocked path set contains the literal pattern `"/users/:id"` (from a route `("/users/:id", UserPage, ...)` without available path parameters)
- **AND** a component calls `ServerFetchPort.fetch("/users/42")` during SSR
- **THEN** the blocked path check SHALL use **segment-count-aware prefix matching**: the pattern `/users/:id` blocks any path that starts with `/users/` AND has exactly the same number of URL segments as the pattern (2 segments for `/users/:id`). `/users/42` SHALL return 500
- **AND** a request to `"/users/42/edit"` (3 segments) SHALL NOT match `"/users/:id"` (2 segments)
- **AND** a multi-segment pattern like `"/users/:id/posts/:postId"` (4 segments) SHALL block `"/users/42/posts/99"` (4 segments, prefix match) but NOT `"/users/42"` (2 segments) or `"/users/42/posts/99/comments/1"` (5 segments)
- **AND** a request to `"/api/users"` SHALL NOT match (prefix does not start with `/users/`)

#### Scenario: Dynamic route with available path parameters uses concrete paths
- **WHEN** the blocked path set contains concrete paths `{"/users/42", "/users/99"}` (from enumerated route parameters during SSG)
- **AND** a component calls `ServerFetchPort.fetch("/users/42")` during SSR
- **THEN** the exact match SHALL return 500
- **AND** a request to `"/users/999"` SHALL NOT match (not in the set), and the ASGI app SHALL process it normally (returning whatever the route handler returns for unmatched paths)

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

#### Scenario: Self-site fetch to a mount path with query parameters
- **WHEN** `base_url="/myapp/"` is configured and `/api` is a configured mount
- **AND** a component calls `await fetch_port.fetch("/api?foo=bar")`
- **THEN** the request SHALL be dispatched as `/api?foo=bar` (without the `base_url` prefix)
- **AND** the query string SHALL be preserved in the dispatched request
- **AND** the request SHALL reach the mounted app in-process via `httpx.ASGITransport`

### Requirement: ServerFetchPort shall be configured from CLI entry points

`create_asgi_app()` and `generate_static_site()` SHALL call `ServerFetchPort.configure()` after creating the ASGI app, providing the app's ASGI instance and blocked paths derived from `app.routes`.

#### Scenario: Dev server configures ServerFetchPort
- **WHEN** `create_asgi_app(app, build_config)` creates the Starlette ASGI app
- **THEN** the `ServerFetchPort` from `app.di_scope` SHALL be configured with the ASGI app and blocked paths
- **AND** blocked paths SHALL be derived from `app.routes`

#### Scenario: SSG configures ServerFetchPort
- **WHEN** `generate_static_site(app)` creates a temporary ASGI app for SSG
- **THEN** the `ServerFetchPort` from `app.di_scope` SHALL be configured with the temporary ASGI app and blocked paths

### Requirement: ServerFetchPort shall return 404 for unknown self-site paths

When a self-site request targets a path that does not match any route in the ASGI app, the `Response` SHALL have `status_code=404`.

#### Scenario: Fetching a non-existent self-site path
- **WHEN** a component calls `await fetch_port.fetch("/nonexistent")` during SSR
- **AND** `"/nonexistent"` does not match any route in the ASGI app
- **THEN** the fetch SHALL return a `Response` with `status_code=404`

### Requirement: Mount path prefixes shall not be blocked for self-site fetch
`blocked_paths` derivation SHALL remain based on page routes only. Paths under a configured ASGI mount prefix SHALL NOT be considered blocked, even if a mounted endpoint shares a path shape with a page route. Self-site fetches to mount paths during SSR/SSG SHALL be routed through the ASGI transport and reach the mounted app in-process, dispatched without `base_url` prefixing per the base_url-resolution requirement.

#### Scenario: Fetching a mounted endpoint during SSR
- **WHEN** a component fetches `/api/users` during SSR and `/api` is a configured mount
- **THEN** the request SHALL be dispatched in-process via `httpx.ASGITransport` to the mounted app
- **AND** the response SHALL be returned to the component and recorded in the transfer cache as with any self-site fetch

#### Scenario: Mount paths never appear in blocked_paths
- **WHEN** `blocked_paths` is computed for an app with page routes and a `/api` mount
- **THEN** no entry in `blocked_paths` SHALL match `/api/...`

### Requirement: ServerFetchPort shall support binding to a root ASGI app

`ServerFetchPort` SHALL support being configured against a root ASGI application that is distinct from WebComPy's internal serving app (embedded deployments). `configure_server_context()` SHALL accept an optional `root_app` parameter; when provided, self-site fetch dispatch SHALL target `root_app` instead of the internal serving app. When `root_app` is `None` (default), behavior SHALL be exactly as before. The mechanism SHALL prevent double-configuration conflicts when the CLI also configures the port (either by deferring the CLI's configuration or by an explicit rebind path).

#### Scenario: root_app provided
- **WHEN** `configure_server_context(app, root_app=host)` is called and the serving app is mounted into `host`
- **THEN** self-site fetches during SSR SHALL be dispatched through `host` via ASGI transport

#### Scenario: Default binding unchanged
- **WHEN** `configure_server_context(app)` is called without `root_app`
- **THEN** self-site fetches SHALL be dispatched through WebComPy's internal serving app as before this change
