# Application Lifecycle

## Purpose

The application lifecycle defines how a WebComPy application starts, runs, and shuts down across its two runtime environments. In the browser, `app.run()` mounts the application to the DOM and keeps it running for the user's session. On the server, module-level functions like `create_asgi_app`, `run_server`, and `generate_static_site` handle development serving and static site generation. The lifecycle also covers property forwarding from the internal `AppDocumentRoot` to the public `WebComPyApp` API.

## Requirements

### Requirement: The application shall provide a browser entry point via app.run()
In the browser (PyScript) environment, `app.run(selector)` SHALL mount and render the application into the DOM element matching the given CSS selector. Calling `run()` in a non-PyScript (server) environment SHALL raise `WebComPyException`. `app.run()` SHALL internally create a single `RenderContext` via `create_render_context()`, which owns the DI scope, Router, AppDocumentRoot, and all rendering state. The `RenderContext`'s DI scope SHALL remain active for the app's lifetime. `on_render_context_init(ctx)` and `on_app_ready(ctx)` SHALL be called on plugins before the first render.

#### Scenario: Running an app with profiling enabled
- **WHEN** a developer creates `WebComPyAppConfig(profile=True)` and calls `app.run()` in the browser
- **THEN** the application SHALL record timestamps for each startup phase (`pyscript_ready`, `init_start`, `imports_done`, `init_done`, `run_start`, `custom_elements_defined`, `run_done`, `loading_removed`, `lazy_preload_start`, `lazy_preloaded`)
- **AND** a formatted profile summary SHALL be printed to the browser console after the loading indicator is removed (in the browser, via a scheduled macro task so any pending lazy-preload batch completes first)
- **AND** `WebComPyApp._record_phase(name)` SHALL record `time.perf_counter()` into `_profile_data` only when `_profile` is True, and SHALL keep only the first occurrence of each phase name
- **AND** `_profile_data` SHALL be owned by the `WebComPyApp` instance (created in `WebComPyApp.__init__`) so that the generated bootstrap script can assign `app._profile_data["pyscript_ready"]` before any RenderContext exists; `RenderContext` SHALL NOT own profile state
- **AND** `WebComPyApp._emit_profile_summary()` SHALL format and output the profile summary — in the browser via `pyscript.context.window.console.log()`, otherwise via `print()`
- **AND** the summary SHALL show elapsed time between phases (`pyscript_ready → imports_done`, `imports_done → init_done`, `init_done → custom_elements_defined`, `custom_elements_defined → run_done`, `run_done → loading_removed`, `lazy_preload_start → lazy_preloaded`) plus a total; a pair whose end timestamp precedes its start timestamp SHALL NOT be shown

#### Scenario: Accessing profile data
- **WHEN** a developer accesses `app.profile_data` on a `WebComPyApp` with `profile=True`
- **THEN** the recorded timestamps dict SHALL be returned
- **WHEN** a developer accesses `app.profile_data` on a `WebComPyApp` with `profile=False`
- **THEN** `None` SHALL be returned

#### Scenario: Running an app with hydration disabled
- **WHEN** a developer creates `WebComPyApp(..., hydrate=False)` in the browser
- **THEN** the application SHALL recreate all DOM nodes from scratch
- **AND** no prerendered DOM node reuse SHALL occur during initial render

#### Scenario: Running an app with hydration enabled (default)
- **WHEN** a developer creates `WebComPyApp(..., hydrate=True)` or uses the default in the browser
- **THEN** the application SHALL attempt to reuse prerendered DOM nodes via `_hydrate_node()`
- **AND** only unmatched nodes SHALL be created via `_init_node()`

#### Scenario: Rendering children with hydration and matching prerendered nodes
- **WHEN** `AppDocumentRoot._render()` is called with `_hydrate=True` and prerendered nodes exist
- **THEN** each child SHALL use `_hydrate_node()` to adopt or create nodes
- **AND** children with matching prerendered nodes SHALL be adopted

#### Scenario: Rendering children with hydration but no prerendered nodes
- **WHEN** `AppDocumentRoot._render()` is called with `_hydrate=True` but no prerendered nodes exist for some children
- **THEN** unmatched children SHALL fall back to normal `_render()` for DOM creation and mounting

#### Scenario: Running an app with default selector
- **WHEN** a developer calls `app.run()` in the browser
- **THEN** the application SHALL mount into the element with `id="webcompy-app"`
- **AND** pre-rendered DOM nodes SHALL be hydrated
- **AND** the loading indicator SHALL be removed after the first render

#### Scenario: Prerendered app root is visible on page load
- **WHEN** the CLI generates HTML with prerendering enabled
- **THEN** the `#webcompy-app` div SHALL NOT have a `hidden` attribute
- **AND** the pre-rendered content SHALL be visible beneath the semi-transparent loading overlay

#### Scenario: Non-prerendered app root is hidden on page load
- **WHEN** the CLI generates HTML with prerendering disabled
- **THEN** the `#webcompy-app` div SHALL have a `hidden` attribute
- **AND** the content SHALL remain invisible until PyScript initializes

#### Scenario: Running an app with custom selector
- **WHEN** a developer calls `app.run("#my-container")` in the browser
- **THEN** the application SHALL mount into the element matching `#my-container`
- **AND** all reactivity, routing, and head management SHALL work as if mounted at the default selector

#### Scenario: Calling run() in a non-browser environment
- **WHEN** a developer calls `app.run()` in a server (non-PyScript) environment
- **THEN** a `WebComPyException` SHALL be raised indicating that `run()` is only available in the browser

#### Scenario: Mounting into a non-existent element
- **WHEN** a developer calls `app.run("#nonexistent")` and no element matches
- **THEN** a `WebComPyException` SHALL be raised indicating the mount point was not found

### MODIFIED: SSR/SSG render path skips hydration
`AppDocumentRoot._render()` SHALL NOT call `child._hydrate_node()` when running in a non-`pyscript` environment. The existing `if self._app and self._app._hydrate and not self.__hydrated:` guard SHALL evaluate `False` in non-pyscript environments because `app._hydrate` is forced to `False` in `WebComPyApp.__init__`. The subsequent `for child in self._children: await child._render()` loop SHALL be the sole render path server-side, and its `await` chain SHALL complete before the caller of `generate_html` proceeds.

#### Scenario: SSG output contains routed page content
- **WHEN** `webcompy generate` produces an HTML file for a route that has a Component child (e.g. `HomePage` inside `RouterView`)
- **THEN** the generated HTML SHALL contain the full component subtree
- **AND** the routed component's DIV SHALL have non-empty children (e.g. `<div webcompy-component="HomePage">...child elements...</div>`)
- **AND** `Component.__init__` for the routed component SHALL execute while the `RenderContext._di_scope` is still active

#### Scenario: Dev server SSR response contains routed page content
- **WHEN** a client requests a route from the dev server (`webcompy start`) and the route has a Component child (e.g. `HomePage` inside `RouterView`)
- **THEN** the HTTP response HTML SHALL contain the full component subtree
- **AND** the routed component's DIV SHALL have non-empty children

### Requirement: The profiling summary shall include startup cost clusters beyond the core phases
When profiling is enabled (`profile=True`), `WebComPyApp._record_phase` SHALL also record startup phases that account for the measured cost clusters: a custom-element bulk-registration phase named `custom_elements_defined` recorded after the hydration-time bulk `customElements.define` pass completes; a lazy-preload start phase named `lazy_preload_start` recorded when the router's lazy-route preload work is scheduled (or begins synchronously on the server); and a lazy-preload completion phase named `lazy_preloaded` recorded when that preload batch finishes executing (in the browser this is inside the scheduled macro task; on the server it is after the synchronous preload loop). Phases SHALL be recorded at most once each (the first occurrence wins). In the browser the formatted summary SHALL be emitted via a scheduled macro task (rather than synchronously at loading-indicator removal) so that any scheduled lazy-preload batch has completed before the summary prints; the elapsed time between these phases SHALL be shown alongside the core lifecycle phases. A pair whose end timestamp precedes its start timestamp SHALL NOT be shown.

#### Scenario: Profiling summary includes the custom-element bulk-registration phase
- **WHEN** an app runs in the browser with `WebComPyAppConfig(profile=True)` and named components are registered before hydration
- **THEN** `app._profile_data` SHALL contain a phase recorded after the bulk custom-element registration pass
- **AND** the formatted profile summary SHALL show the elapsed time associated with that phase

#### Scenario: Profiling summary includes the lazy-preload span
- **WHEN** an app with lazy routes runs with `profile=True` and `preload=True` (default)
- **THEN** `app._profile_data` SHALL contain `lazy_preload_start` recorded when the preload batch is scheduled and `lazy_preloaded` recorded when the batch completes
- **AND** the formatted profile summary SHALL show the elapsed time between them

#### Scenario: Phases are recorded at most once
- **WHEN** a profiled phase's recording site is reached more than once during a run
- **THEN** only the first occurrence SHALL be recorded in `app._profile_data`

#### Scenario: Profiling remains disabled by default
- **WHEN** `profile=False` (the default) and an app runs
- **THEN** no new phase timestamps SHALL be recorded, preserving the zero-overhead default behavior

### Requirement: The application shall create a RenderContext per request on the server
On the server, `app.create_render_context(path)` SHALL create a fresh `RenderContext` for each SSR request. The `RenderContext` SHALL own all mutable rendering state: DI scope, Router, AppDocumentRoot, HeadPropsStore, Signal graph state, and deferred rendering state. After rendering, `RenderContext.dispose()` SHALL clean up all request-scoped resources. In the browser, `app.run()` SHALL internally create a single long-lived `RenderContext`.

#### Scenario: Per-request RenderContext on the server
- **WHEN** `create_asgi_app(app)` serves multiple HTTP requests
- **THEN** each request SHALL create a new `RenderContext` via `app.create_render_context(path)`
- **AND** no mutable state from one request SHALL leak into another
- **AND** `RenderContext.dispose()` SHALL be called after HTML is generated

#### Scenario: Single RenderContext in the browser
- **WHEN** `app.run()` is called in the browser
- **THEN** a single `RenderContext` SHALL be created internally
- **AND** the `RenderContext` SHALL remain active for the entire browser session

### Requirement: The server entry point shall be a module-level function
Server-side entry points SHALL be module-level functions (`create_asgi_app`, `run_server`) that accept a `WebComPyApp` instance and optional typed config dataclasses (`create_asgi_app(app, server_config=None)`). Dev mode is no longer a separate parameter — it is controlled by `ServerConfig.dev`. This avoids importing server-only dependencies (starlette, uvicorn) in the browser environment. Internally, CLI functions read `AppConfig` from `app.config` and pass `ServerConfig`/`GenerateConfig` as separate arguments; there is no conversion between config types.

#### Scenario: Creating an ASGI app from a WebComPyApp
- **WHEN** a developer calls `create_asgi_app(app)` on the server
- **THEN** a Starlette ASGI application SHALL be returned
- **AND** the ASGI app SHALL serve all routes, static files, and app packages
- **AND** default `ServerConfig()` values SHALL be used

#### Scenario: Creating an ASGI app with custom server config
- **WHEN** a developer calls `create_asgi_app(app, server_config=ServerConfig(port=3000, dev=True))`
- **THEN** the ASGI app SHALL serve on port 3000 with hot-reload enabled

#### Scenario: Starting a dev server with run_server
- **WHEN** a developer calls `run_server(app)` or `python -m webcompy start`
- **THEN** a uvicorn server SHALL start on the configured port (default 8080)
- **AND** hot-reload SHALL be enabled when `ServerConfig.dev` is `True` or `--dev` flag is set
- **AND** CLI flags SHALL override config file values

#### Scenario: Starting a dev server via CLI with app_import_path
- **WHEN** a developer runs `python -m webcompy start` and `webcompy_config.py` at the project root defines `app_import_path`
- **THEN** the CLI SHALL discover the app instance via `app_import_path`
- **AND** `webcompy_config.py` SHALL be used for `AppConfig`
- **AND** `webcompy_server_config.py` SHALL be used for `ServerConfig` if present

#### Scenario: Starting a dev server via CLI with --app flag
- **WHEN** a developer runs `python -m webcompy start --app my_app.bootstrap:app`
- **THEN** the CLI SHALL import `my_app.bootstrap` and use the `app` attribute
- **AND** `webcompy_config.py` SHALL NOT be required
- **AND** `webcompy_server_config.py` SHALL be searched first in the app package (`my_app.webcompy_server_config`), then at the project root

### Requirement: The SSG entry point shall be a module-level function
Static site generation SHALL use a module-level function (`generate_static_site`) that accepts a `WebComPyApp` instance and an optional `GenerateConfig`. The SSG process SHALL enter the app's DI scope for the entire generation pipeline (from dist configuration through HTML rendering) to ensure all `inject()` calls during route rendering and head management succeed.

#### Scenario: Generating a static site from a WebComPyApp
- **WHEN** a developer calls `generate_static_site(app)` on the server
- **THEN** a `dist/` directory SHALL be created with pre-rendered HTML for each route
- **AND** a bundled Python wheel SHALL be included
- **AND** static files SHALL be copied
- **AND** a `.nojekyll` file SHALL be created

#### Scenario: Generating with custom config
- **WHEN** a developer calls `generate_static_site(app, generate_config=GenerateConfig(dist="out", cname="example.com"))`
- **THEN** output SHALL be written to the `out` directory
- **AND** a `CNAME` file SHALL be created with `example.com`

#### Scenario: Generating via CLI with config files
- **WHEN** a developer runs `python -m webcompy generate`
- **THEN** the CLI SHALL discover the app instance via `webcompy_config.py` at the project root or `--app`
- **AND** `generate_config` SHALL be read from `webcompy_server_config.py` (searched in the app package first when `--app` is used, then at the project root)

### Requirement: WebComPyApp shall forward AppDocumentRoot properties
`WebComPyApp` SHALL provide transparent access to frequently used `AppDocumentRoot` properties when a `RenderContext` exists. The following properties and methods SHALL be forwarded: `routes`, `router_mode`, `set_path`, `head`, `scoped_styles`, `scripts`, `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`, `set_html_attr`, `remove_html_attr`, `html_attrs`. When no `RenderContext` exists, these SHALL raise `AttributeError`. `app.di_scope` SHALL delegate to `RenderContext.di_scope` when a `RenderContext` exists, and raise `AttributeError` otherwise.

#### Scenario: Accessing app routes
- **WHEN** a developer accesses `app.routes`
- **THEN** the route list SHALL be returned (or `None` if no router)

#### Scenario: Setting the path programmatically
- **WHEN** a developer calls `app.set_path("/users/42")`
- **THEN** the router SHALL navigate to `/users/42`

#### Scenario: Accessing head management
- **WHEN** a developer calls `app.set_title("My Page")` or accesses `app.head`
- **THEN** the corresponding head management SHALL work correctly

#### Scenario: Accessing router_mode
- **WHEN** a developer accesses `app.router_mode`
- **THEN** the result SHALL be the router mode string (or `None` if no router)

#### Scenario: Accessing scoped_styles
- **WHEN** a developer accesses `app.scoped_styles`
- **THEN** the result SHALL be a `dict[str, str]` mapping component cid values to CSS strings
- **AND** the dict SHALL be sorted by cid for deterministic ordering

#### Scenario: Accessing style (removed)
- **WHEN** a developer attempts to access `app.style`
- **THEN** an `AttributeError` SHALL be raised (property removed)

### Requirement: SSR/SSG entry points shall await pending tasks before context disposal

All server-side rendering entry points (`generate_html()` in `webcompy_server._html`, the ASGI HTML handler in `webcompy_cli._server`, and the SSG route fetch loop in `webcompy_cli._generate`) SHALL call `await scheduler.await_pending()` after the render tree completes (`await ctx._root._render()`) and before `ctx.dispose()`. The scheduler SHALL be obtained from the render context's DI scope via `inject(ASYNC_SCHEDULER_PORT_KEY)`. This guarantees that all tasks scheduled during the render (via `aio_run`, `DynamicElement._hydrate_node`, `SuspenseElement`, etc.) complete before the DI scope is torn down.

#### Scenario: generate_html drains tasks before disposal
- **WHEN** `generate_html()` is called during SSR or SSG
- **THEN** after `await ctx._root._render()` completes
- **AND** before `ctx.dispose()` is called
- **AND** `await scheduler.await_pending()` SHALL be invoked to drain all registered tasks

#### Scenario: ASGI handler drains tasks before disposal
- **WHEN** the ASGI HTML handler processes a request
- **THEN** after the render tree completes
- **AND** before `ctx.dispose()` is called
- **AND** `await scheduler.await_pending()` SHALL be invoked

### Requirement: app._hydrate shall remain environment-guarded as defense-in-depth

`WebComPyApp.__init__` SHALL set `self._hydrate = self._config.hydrate and ENVIRONMENT == "pyscript"`. This guard remains in place as a defense-in-depth measure. The `AsyncSchedulerPort` provides the primary structural guarantee (task completion before disposal), and the environment guard ensures hydration-related scheduling is never attempted on the server even if the port's drain is bypassed.

#### Scenario: Hydration disabled on server
- **WHEN** a `WebComPyApp` is created in a non-pyscript environment with `WebComPyAppConfig(hydrate=True)`
- **THEN** `app._hydrate` SHALL be `False`
- **AND** `AppDocumentRoot._render()` SHALL skip the `_hydrate_node()` recursion
- **AND** all children SHALL be rendered via the synchronous `await child._render()` path

### Requirement: Browser startup shall register named custom elements before hydration

When `app.run()` starts in the browser, the application SHALL register currently known named component custom elements before calling child `_hydrate_node()` methods. Registration SHALL occur early enough for SSR nodes to upgrade, while server and SSG entry points SHALL skip registration.

#### Scenario: Starting hydration with named components
- **WHEN** `app.run()` starts with pre-rendered named component markup
- **THEN** the named custom-element definitions SHALL be registered before child hydration
- **AND** hydration SHALL adopt upgraded existing nodes instead of replacing them

#### Scenario: Starting without named components
- **WHEN** an application contains only unnamed components
- **THEN** startup SHALL not perform custom-element registration
- **AND** the existing hydration sequence SHALL remain unchanged

#### Scenario: Running SSR or SSG
- **WHEN** the application renders through a server-side entry point
- **THEN** no browser custom-element registry or FFI callback SHALL be accessed
- **AND** generated HTML SHALL contain any named custom-element tags normally

### Requirement: Browser startup shall make named custom elements available before first creation

Named component generators that are resolved during or after initial application startup SHALL be registered before their first DOM node creation or hydration adoption. Registration failures SHALL propagate as framework component errors and SHALL not leave a partially initialized application silently running.

#### Scenario: Resolving a named lazy route
- **WHEN** a lazy route resolves a named component during navigation
- **THEN** the custom element SHALL be registered before the route component creates or adopts its wrapper
- **AND** the route SHALL render using the registered custom element

#### Scenario: Registration failure during startup
- **WHEN** a named element conflicts with an incompatible existing custom-element definition
- **THEN** `app.run()` SHALL report a `WebComPyComponentException`
- **AND** hydration SHALL not proceed as if the component were registered