# SSG via SSR

## Purpose

Static site generation and the dev/prod server currently use separate code paths to produce HTML, leading to duplicated setup logic and potential output divergence. By restructuring SSG to reuse the ASGI app (SSR pipeline), we ensure identical HTML output, eliminate code duplication, and enable async rendering in the SSR pipeline.

Three serving modes produce HTML through the same `create_asgi_app()` → `send_html()` → `generate_html()` pipeline:

| Mode | CLI invocation | Hot reload | SSE | Purpose |
|---|---|---|---|---|
| Dev server | `webcompy start --dev` | Yes | Included | Development |
| Prod server | `webcompy start` | No | Excluded | Production |
| SSG | `webcompy generate` | No | Excluded | Static export |

## Requirements

### Requirement: generate_static_site() shall use ASGITransport to produce static HTML
`generate_static_site()` SHALL call `create_asgi_app(mode="prod")` to obtain a `_ServingApp` wrapper and fetch each route using `httpx.AsyncClient(transport=ASGITransport(app=serving.asgi))`. For history-mode apps, `_preload()` SHALL be called on each page component BEFORE entering the `httpx.AsyncClient` context, as it is semantically independent of ASGITransport route fetching. The response HTML for each route SHALL be written to the appropriate file in the dist directory. This ensures SSG output is identical to dev/prod server output.

#### Scenario: Generating a static site for a history-mode app
- **WHEN** `generate_static_site(app)` is called for an app with `router_mode="history"` and multiple routes
- **THEN** a `_ServingApp` wrapper SHALL be created via `create_asgi_app(mode="prod")`
- **AND** `_preload()` SHALL be called on each page component before the httpx context
- **AND** each route SHALL be fetched via `httpx.AsyncClient` with `ASGITransport(app=serving.asgi)`
- **AND** the response HTML for each route SHALL be written to `dist/{path}/index.html`
- **AND** a 404 page SHALL be generated for unmatched paths

#### Scenario: Generating a static site for a hash-mode app
- **WHEN** `generate_static_site(app)` is called for an app with `router_mode="hash"`
- **THEN** the root route `/` SHALL be fetched via `httpx.AsyncClient` with `ASGITransport`
- **AND** the response HTML SHALL be written to `dist/index.html`

#### Scenario: SSG output matches server output
- **WHEN** the same `WebComPyApp` is served via the dev/prod server and generated via SSG
- **THEN** the HTML produced for each route SHALL be identical between server and SSG
- **AND** the same DI scope, path resolution, and rendering pipeline SHALL be exercised in both cases

### Requirement: generate_html() shall be async (provided by async-rendering-pipeline)

`generate_html()` SHALL be an `async def` function with the signature `async def generate_html(...) -> str`. Callers SHALL `await` the result. This requirement is defined in `feat/async-rendering-pipeline` (`async-rendering/spec.md`). This change depends on that requirement and constrains its SSR/SSG callers.

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

When `generate_static_site()` fetches each route via `httpx.ASGITransport`, the ASGI request goes through the same `send_html()` handler used by the dev/prod server. This handler already creates a fresh `RenderContext` for each request via `app.create_render_context(path)` in a `try/finally` block and SHALL call `RenderContext.dispose()` in the `finally` block. ASGITransport requests SHALL go through the same handler, so per-route disposal is already guaranteed by the existing handler logic — no additional SSG-specific disposal code is needed.

If a route fetch raises an exception, `dispose()` SHALL still be called via the `finally` block in `send_html()` to prevent resource leaks (DI scopes, component stores, etc.).

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
Dependency resolution, lockfile handling, WASM/runtime asset management, and wheel building logic SHALL be extracted from `_generate.py` and `_server.py` into a shared `resolve_build_artifacts()` function. `create_asgi_app()` SHALL be the sole caller of `resolve_build_artifacts()`; `_generate.py` SHALL obtain `BuildArtifacts` from the `_ServingApp.artifacts` field returned by `create_asgi_app()` rather than calling `resolve_build_artifacts()` directly. `cdn_temp_dir_obj` lifecycle SHALL be managed exclusively by `create_asgi_app()`, which SHALL call `__exit__()` on it immediately after wheel building.

#### Scenario: Dev/prod server uses shared setup
- **WHEN** `create_asgi_app()` is called
- **THEN** it SHALL call `resolve_build_artifacts()` to obtain build artifacts
- **AND** use those artifacts to create the ASGI app routes

#### Scenario: SSG uses shared setup
- **WHEN** `generate_static_site()` is called
- **THEN** it SHALL call `create_asgi_app()` to obtain a `_ServingApp` wrapper
- **AND** read `_ServingApp.artifacts` to access `BuildArtifacts`
- **AND** SHALL NOT call `resolve_build_artifacts()` directly
- **AND** SHALL NOT manage `cdn_temp_dir_obj` lifecycle (handled by `create_asgi_app()`)

#### Scenario: Build artifacts dataclass contains all resolved data
- **THEN** `BuildArtifacts` SHALL include `app_version`, `wheel_filename`, `extra_wheel_filenames`, `pyodide_package_names`, `wasm_local_urls`, `lockfile_url`, `runtime_serving`, and mode-specific fields (in-memory file maps for dev/prod, dist directory for SSG)

### Requirement: create_asgi_app() shall accept a prod/dev mode parameter
`create_asgi_app()` SHALL accept a `mode` parameter with values `"prod"` (default) and `"dev"`. The mode SHALL be the single source of truth for dev-vs-prod behavior: it SHALL set `build_config.server.dev`, control SSE endpoint inclusion, and control dev-mode cache headers.

#### Scenario: Creating an ASGI app for dev mode
- **WHEN** `create_asgi_app(app, build_config, mode="dev")` is called
- **THEN** `build_config.server.dev` SHALL be set to `True`
- **AND** the SSE reload endpoint `/_webcompy_reload` SHALL be included
- **AND** dev-mode cache headers SHALL be set on wheel files

#### Scenario: Creating an ASGI app for prod mode
- **WHEN** `create_asgi_app(app, build_config, mode="prod")` is called
- **THEN** `build_config.server.dev` SHALL be set to `False`
- **AND** the SSE reload endpoint SHALL NOT be included
- **AND** dev-mode cache headers SHALL NOT be set on wheel files

#### Scenario: Creating an ASGI app with default mode
- **WHEN** `create_asgi_app(app, build_config)` is called without specifying a mode
- **THEN** it SHALL behave identically to `mode="prod"`
- **AND** `build_config.server.dev` SHALL be `False`

### Requirement: create_asgi_app() shall remain synchronous; hash-mode pre-rendering shall be a separate step

`create_asgi_app()` SHALL remain a synchronous function that returns a `_ServingApp` wrapper. The wrapper provides `asgi` (the underlying `Starlette` ASGI instance), `html_generator`, `hash_cache`, and `artifacts` (the `BuildArtifacts` instance) as typed attributes. `create_asgi_app()` SHALL NOT perform any async operations during construction. For hash-mode apps that need pre-rendered HTML cached at startup, a separate async function `_pre_render_hash_mode_html(app, html_generator)` SHALL be called after `create_asgi_app()` returns, producing the cached HTML that the hash-mode handler returns on every request. If `_pre_render_hash_mode_html()` raises an exception (e.g., due to a component rendering error during pre-rendering), the error SHALL propagate to the caller and the ASGI app SHALL NOT be started. This separation keeps `create_asgi_app()` usable with `uvicorn.run()` (which expects a synchronous app factory) and avoids unnecessary async complexity for the common history-mode case.

#### Scenario: Creating an ASGI app for a hash-mode app
- **WHEN** `create_asgi_app()` is called for a hash-mode app
- **THEN** it SHALL return a `_ServingApp` wrapper whose `.asgi` contains a synchronous handler returning pre-cached HTML
- **AND** `_pre_render_hash_mode_html(app)` SHALL be called afterward to generate and cache the HTML

#### Scenario: Creating an ASGI app for a history-mode app
- **WHEN** `create_asgi_app()` is called for a history-mode app
- **THEN** it SHALL return a `_ServingApp` wrapper
- **AND** no async pre-rendering SHALL be performed (each request renders dynamically)

#### Scenario: Calling create_asgi_app() from run_server()
- **WHEN** `run_server()` needs to create the ASGI app
- **THEN** it SHALL call `create_asgi_app()` synchronously to obtain a `_ServingApp` wrapper
- **AND** the mode SHALL be `"dev"` if the `--dev` CLI flag is present, otherwise `"prod"`
- **AND** for hash-mode, it SHALL call `asyncio.run(_pre_render_hash_mode_html(app))` after creation
- **AND** `serving.asgi` SHALL be passed to `uvicorn.run()` which expects a synchronous ASGI instance
- **AND** `run_server()` SHALL remain a synchronous function
- **AND** `build_config.server.dev` SHALL be read after `create_asgi_app()` returns to configure uvicorn file-watching reload

#### Scenario: Hash-mode pre-rendering raises during component rendering
- **WHEN** `_pre_render_hash_mode_html(app)` is called for a hash-mode app
- **AND** a component raises during SSR (e.g., an async setup fails, or a blocked fetch triggers a 500)
- **THEN** the error SHALL propagate to the caller
- **AND** the error SHALL propagate to the caller and abort server startup
- **AND** the ASGI app SHALL NOT be started
- **AND** RenderContext SHALL be disposed via `finally` block before the exception propagates

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

### Requirement: _ServingApp shall expose BuildArtifacts via artifacts field

The `_ServingApp` wrapper returned by `create_asgi_app()` SHALL include an `artifacts: BuildArtifacts` typed field containing the resolved build artifacts. This allows callers to access wheel filenames, in-memory file maps, and asset file paths without calling `resolve_build_artifacts()` independently.

#### Scenario: Accessing build artifacts from _ServingApp
- **WHEN** `create_asgi_app()` returns a `_ServingApp` wrapper
- **THEN** the wrapper's `artifacts` field SHALL contain the `BuildArtifacts` instance produced by the internal `resolve_build_artifacts()` call
- **AND** `serving.artifacts.app_package_files` SHALL contain the wheel byte content
- **AND** `serving.artifacts.wheel_filename` SHALL contain the app wheel filename
- **AND** `serving.artifacts` SHALL be accessible after `create_asgi_app()` returns (no cleanup occurs until the wrapper is discarded)

### Requirement: generate_app_version() shall produce deterministic output when no explicit version is configured

When `generate_app_version()` is called without an explicit version string, it SHALL return a deterministic, stable value. It SHALL NOT use wall-clock time, random values, or other non-deterministic sources. The intermediate version is an implementation detail used only for initial wheel construction before `_content_hash_wheel()` replaces it with the content-based hash.

#### Scenario: Calling generate_app_version() twice with no explicit version
- **WHEN** `generate_app_version()` is called twice with `app_version=None`
- **THEN** both calls SHALL return the same value

#### Scenario: Calling generate_app_version() with an explicit version
- **WHEN** `generate_app_version(app_version="1.2.3")` is called
- **THEN** it SHALL return `"1.2.3"` unchanged

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

A statically deployed site has no live mount endpoints: only responses fetched from mounts during generation are available, replayed through the hydration transfer payload. Runtime-only fetches against mounts will fail on static hosting unless baked at build time.

### Requirement: Generated pages SHALL be independent of route generation order

The HTML output of each generated route — including the scoped-style elements in the `<head>` and the hydration transfer payload — SHALL NOT depend on which other routes were generated before it. Generating the same site twice, or generating a subset of routes, SHALL produce identical per-route output (aside from build metadata that is intentionally shared, such as version hashes). Any state accumulated while generating one route SHALL NOT leak into another route's output.

#### Scenario: Page generated first vs. last
- **WHEN** a site with routes `/a` and `/b` is generated in the order `/a`, `/b`
- **AND** the same site is generated in the order `/b`, `/a`
- **THEN** the HTML for `/a` SHALL be byte-identical in both runs
- **AND** the HTML for `/b` SHALL be byte-identical in both runs

#### Scenario: Layout-only component styles on later pages
- **WHEN** a nested route uses a lazily loaded layout that imports additional styled components
- **THEN** pages under that route SHALL contain those components' scoped styles whether they are generated first, in the middle, or last

#### Scenario: Payload does not accumulate across routes
- **WHEN** route `/a` loads resource `a.md` and route `/b` loads resource `b.md` during SSG with the default transfer mode
- **THEN** `/b`'s payload SHALL NOT contain `a.md`, regardless of generation order
