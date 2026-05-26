# SSG via SSR

## Purpose

Static site generation and the dev server currently use separate code paths to produce HTML, leading to duplicated setup logic and potential output divergence. By restructuring SSG to reuse the ASGI app (SSR pipeline), we ensure identical HTML output, eliminate code duplication, and enable async rendering in the SSR pipeline.

## ADDED Requirements

### Requirement: generate_static_site() shall use ASGITransport to produce static HTML
`generate_static_site()` SHALL create an ASGI app via `create_asgi_app()` and fetch each route using `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))`. The response HTML for each route SHALL be written to the appropriate file in the dist directory. This ensures SSG output is identical to dev server output.

#### Scenario: Generating a static site for a history-mode app
- **WHEN** `generate_static_site(app)` is called for an app with `router_mode="history"` and multiple routes
- **THEN** an ASGI app SHALL be created with `mode="ssg"`
- **AND** each route SHALL be fetched via `httpx.AsyncClient` with `ASGITransport`
- **AND** the response HTML for each route SHALL be written to `dist/{path}/index.html`
- **AND** a 404 page SHALL be generated for unmatched paths

#### Scenario: Generating a static site for a hash-mode app
- **WHEN** `generate_static_site(app)` is called for an app with `router_mode="hash"`
- **THEN** the root route `/` SHALL be fetched via `httpx.AsyncClient` with `ASGITransport`
- **AND** the response HTML SHALL be written to `dist/index.html`

#### Scenario: SSG output matches dev server output
- **WHEN** the same `WebComPyApp` is served via the dev server and generated via SSG
- **THEN** the HTML produced for each route SHALL be identical between dev server and SSG
- **AND** the same DI scope, path resolution, and rendering pipeline SHALL be exercised in both cases

### Requirement: generate_html() shall be async (provided by async-rendering-pipeline)

`generate_html()` SHALL be an `async def` function returning `Awaitable[str]`. This requirement is defined in `feat/async-rendering-pipeline` (`async-rendering/spec.md`). This change depends on that requirement and constrains its SSR/SSG callers.

#### Scenario: Calling generate_html() from send_html()
- **WHEN** `send_html()` in `_server.py` needs to render HTML
- **THEN** it SHALL `await html_generator()` to get the HTML string

#### Scenario: Calling generate_html() during hash mode pre-rendering
- **WHEN** `create_asgi_app()` pre-renders HTML for a hash-mode app at startup
- **THEN** it SHALL `await html_generator()` to get the HTML string

#### Scenario: Calling generate_html() from test code
- **WHEN** test code calls `generate_html()` directly
- **THEN** it SHALL use `await generate_html(...)` in an async context or `asyncio.run(generate_html(...))`

### Requirement: send_html() shall be async and await html_generator()
The `send_html()` route handler in `_server.py` SHALL be `async def send_html()` and SHALL await `html_generator()` instead of calling it synchronously. This is required because `generate_html()` is now async.

#### Scenario: Handling a history-mode request
- **WHEN** a request arrives for a history-mode route
- **THEN** `send_html()` SHALL enter `app.di_scope`, set the path, `await html_generator()`, and return `HTMLResponse(html)`

#### Scenario: Handling a hash-mode request
- **WHEN** a request arrives for a hash-mode app
- **THEN** the pre-rendered HTML SHALL be returned without awaiting per-request rendering

### Requirement: Per-route RenderContext lifecycle shall be guaranteed during SSG

When `generate_static_site()` fetches each route via `httpx.ASGITransport`, the ASGI handler SHALL create a fresh `RenderContext` for each request and SHALL call `RenderContext.dispose()` after the HTML is generated. If a route fetch raises an exception, `dispose()` SHALL still be called via `try/finally` to prevent resource leaks (DI scopes, component stores, etc.).

#### Scenario: RenderContext is disposed after successful route rendering
- **WHEN** a route `/about` is fetched via ASGITransport during SSG
- **AND** the HTML is generated successfully
- **THEN** `RenderContext.dispose()` SHALL be called before the response is returned
- **AND** the route's DI scope and component store SHALL be cleaned up

#### Scenario: RenderContext is disposed after route fetch error
- **WHEN** a route `/bad-page` is fetched during SSG
- **AND** component rendering raises an exception
- **THEN** `RenderContext.dispose()` SHALL still be called in a `finally` block
- **AND** no resource leak SHALL occur
- **AND** the exception SHALL propagate to `generate_static_site()` for error handling

### Requirement: Shared setup logic shall be extracted into _resolve_build_artifacts()
Dependency resolution, lockfile handling, WASM/runtime asset management, and wheel building logic SHALL be extracted from `_generate.py` and `_server.py` into a shared `_resolve_build_artifacts()` function. Both modules SHALL call this function instead of duplicating the logic.

#### Scenario: Dev server uses shared setup
- **WHEN** `create_asgi_app()` is called for dev mode
- **THEN** it SHALL call `resolve_build_artifacts()` to obtain build artifacts
- **AND** use those artifacts to create the ASGI app routes

#### Scenario: SSG uses shared setup
- **WHEN** `generate_static_site()` is called
- **THEN** it SHALL call `resolve_build_artifacts()` to obtain build artifacts
- **AND** use those artifacts to create the ASGI app via `create_asgi_app()`

#### Scenario: Build artifacts dataclass contains all resolved data
- **THEN** `BuildArtifacts` SHALL include `app_version`, `wheel_filename`, `extra_wheel_filenames`, `pyodide_package_names`, `wasm_local_urls`, `lockfile_url`, `runtime_serving`, and mode-specific fields (in-memory file maps for dev, dist directory for SSG)

### Requirement: create_asgi_app() shall accept a mode parameter
`create_asgi_app()` SHALL accept a `mode` parameter with values `"dev"` (default) and `"ssg"`. In SSG mode, dev-only features SHALL be excluded.

#### Scenario: Creating an ASGI app for dev mode
- **WHEN** `create_asgi_app(app, build_config, mode="dev")` is called
- **THEN** the SSE reload endpoint `/_webcompy_reload` SHALL be included
- **AND** dev-mode cache headers SHALL be set on wheel files

#### Scenario: Creating an ASGI app for SSG mode
- **WHEN** `create_asgi_app(app, build_config, mode="ssg")` is called
- **THEN** the SSE reload endpoint SHALL NOT be included
- **AND** dev-mode cache headers SHALL NOT be set on wheel files
- **AND** `build_config.server.dev` SHALL be forced to `False`

### Requirement: create_asgi_app() shall be async for hash mode pre-rendering
`create_asgi_app()` SHALL be `async def` to support awaiting `html_generator()` for hash mode pre-rendering at startup. Callers SHALL await the result.

#### Scenario: Creating an ASGI app for a hash-mode app
- **WHEN** `create_asgi_app()` is called for a hash-mode app
- **THEN** the HTML SHALL be pre-rendered once by awaiting `html_generator()`
- **AND** the cached HTML SHALL be served for all requests without per-request rendering

#### Scenario: Creating an ASGI app for a history-mode app
- **WHEN** `create_asgi_app()` is called for a history-mode app
- **THEN** `send_html()` SHALL await `html_generator()` per request

#### Scenario: Calling create_asgi_app() from run_server()
- **WHEN** `run_server()` needs to create the ASGI app
- **THEN** it SHALL call `asyncio.run(create_asgi_app(...))` to resolve the async factory, obtaining the synchronous ASGI app
- **AND** the resolved ASGI app SHALL be passed to `uvicorn.run()` which expects a synchronous app factory or ASGI instance
- **AND** `run_server()` SHALL remain a synchronous function (it uses `asyncio.run()` internally)

#### Scenario: Calling create_asgi_app() from async code
- **WHEN** async code calls `await create_asgi_app(...)` directly
- **THEN** the ASGI app SHALL be returned for use within the existing event loop
- **AND** no separate event loop SHALL be created

### Requirement: generate_static_site() shall be async with asyncio.run() CLI wrapper
`generate_static_site()` SHALL be an `async def` function. The CLI entry point SHALL call `asyncio.run(generate_static_site())`. Programmatic callers MAY use `await generate_static_site(app)` or `asyncio.run(generate_static_site(app))`.

#### Scenario: Running SSG from CLI
- **WHEN** a developer runs `python -m webcompy generate`
- **THEN** the CLI SHALL call `asyncio.run(generate_static_site())` to execute the async function

#### Scenario: Running SSG programmatically
- **WHEN** a developer calls `await generate_static_site(app)` from async code
- **THEN** SSG SHALL execute within the existing event loop

#### Scenario: Running SSG programmatically from sync code
- **WHEN** a developer calls `asyncio.run(generate_static_site(app))` from synchronous code
- **THEN** SSG SHALL create a new event loop and execute

### Requirement: Blocked paths shall prevent infinite recursion during SSR
When `ServerFetchPort` makes a fetch request during SSR that targets a page route served by the same ASGI app, the request SHALL return a 500 error instead of causing infinite recursion. This is handled by the `feat/server-fetch-port-asgi` change.

#### Scenario: Component fetches a page route during SSR
- **WHEN** a component calls `HttpClient.get("/api/data")` during SSR
- **AND** `/api/data` is a page route (not an API endpoint)
- **THEN** the ServerFetchPort SHALL return a 500 error
- **AND** no infinite recursion SHALL occur

#### Scenario: Component fetches a non-page route during SSR
- **WHEN** a component calls `HttpClient.get("/_webcompy-app-package/app.whl")` during SSR
- **THEN** the request SHALL succeed normally
- **AND** the wheel file content SHALL be returned