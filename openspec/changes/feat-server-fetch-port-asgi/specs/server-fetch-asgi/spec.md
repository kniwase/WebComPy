# Server Fetch ASGI

## Purpose

Enable WebComPy components to fetch data from their own application's API endpoints during server-side rendering (SSR) and static site generation (SSG). Self-site requests are routed through the app's own ASGI app via `httpx.ASGITransport`, eliminating network I/O and enabling data fetching without a running server. Page routes that return HTML are blocked with a 500 status to prevent infinite recursion during rendering.

## ADDED Requirements

### Requirement: FetchPort shall classify URLs as self-site or external

`FetchPort` SHALL provide a non-abstract `is_self_site_url(url)` method with a default implementation returning `False`. This ensures backward compatibility with existing `FetchPort` implementations (including `BrowserFetchPort` and custom ports) that don't need self-site routing. URLs starting with `/` (absolute path) or `.` (relative path) SHALL be classified as self-site. All other URLs SHALL be classified as external.

Relative URLs starting with `.` SHALL be resolved against `base_url` root, not the current route path. For example, with `base_url="/myapp/"`, a fetch to `./api/data` resolves to `/myapp/api/data`.

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

Page routes (routes that have a corresponding `Component` registered via `app.routes`) SHALL be blocked during self-site fetch to prevent infinite recursion. Blocked paths SHALL be derived from `app.routes` — any route tuple `(path, page_component, *_rest)` where `page_component` is not `None` SHALL be considered a page route. Dynamic route segments (e.g., `/users/:id`) SHALL be converted to concrete paths using their path parameters before being added to the blocked paths set. Routes without path parameters that have dynamic segments SHALL be included as-is using the literal route pattern string (e.g., `/users/:id`). When a blocked path is requested, `ServerFetchPort` SHALL return a `Response` with `status_code=500` and a descriptive error message.

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

### Requirement: ServerFetchPort shall resolve self-site URLs against base_url

When `base_url` is configured on the app (e.g., `/myapp/`), self-site absolute paths SHALL be resolved with the `base_url` prefix. For example, with `base_url="/myapp/"`, a fetch to `/api/data` SHALL be routed to `/myapp/api/data`.

#### Scenario: Self-site fetch with base_url
- **WHEN** `base_url="/myapp/"` is configured
- **AND** a component calls `await fetch_port.fetch("/api/data")`
- **THEN** the request SHALL be routed to `/myapp/api/data` within the ASGI app

#### Scenario: Self-site fetch with default base_url
- **WHEN** `base_url="/"` is the default
- **AND** a component calls `await fetch_port.fetch("/api/data")`
- **THEN** the request SHALL be routed to `/api/data` within the ASGI app

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