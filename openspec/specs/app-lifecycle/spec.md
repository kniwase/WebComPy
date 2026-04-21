# Application Lifecycle

## Purpose

The application lifecycle defines how a WebComPy application starts, runs, and shuts down across its two runtime environments. In the browser, `app.run()` mounts the application to the DOM and keeps it running for the user's session. On the server, module-level functions like `create_asgi_app`, `run_server`, and `generate_static_site` handle development serving and static site generation. The lifecycle also covers property forwarding from the internal `AppDocumentRoot` to the public `WebComPyApp` API.

## Requirements

### Requirement: The application shall provide a browser entry point via app.run()
In the browser (PyScript) environment, `app.run(selector)` SHALL mount and render the application into the DOM element matching the given CSS selector. The `selector` parameter SHALL default to `"#webcompy-app"` for backward compatibility. Calling `run()` in a non-PyScript (server) environment SHALL raise `WebComPyException`. In the browser, the DI scope SHALL be activated at `WebComPyApp` creation time via `__enter__()` without `__exit__()` (i.e., the scope remains active for the app's lifetime). In the server environment, the scope SHALL be entered/exited per-operation via `with app.di_scope:`.

#### Scenario: Running an app with profiling enabled
- **WHEN** a developer creates `WebComPyApp(..., profile=True)` and calls `app.run()` in the browser
- **THEN** the application SHALL record timestamps for each startup phase (`pyscript_ready`, `init_start`, `imports_done`, `init_done`, `run_start`, `run_done`, `loading_removed`)
- **AND** a formatted profile summary SHALL be printed to the browser console after the loading indicator is removed

#### Scenario: Running an app with hydration disabled
- **WHEN** a developer creates `WebComPyApp(..., hydrate=False)` in the browser
- **THEN** the application SHALL recreate all DOM nodes from scratch
- **AND** no prerendered DOM node reuse SHALL occur during initial render

#### Scenario: Running an app with hydration enabled (default)
- **WHEN** a developer creates `WebComPyApp(..., hydrate=True)` or uses the default in the browser
- **THEN** the application SHALL attempt to reuse prerendered DOM nodes via `_hydrate_node()`
- **AND** only unmatched nodes SHALL be created via `_init_node()`

#### Scenario: Running an app with default selector
- **WHEN** a developer calls `app.run()` in the browser
- **THEN** the application SHALL mount into the element with `id="webcompy-app"`
- **AND** pre-rendered DOM nodes SHALL be hydrated
- **AND** the loading indicator SHALL be removed after the first render

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
`WebComPyApp` SHALL provide transparent access to frequently used `AppDocumentRoot` properties. The following properties and methods SHALL be forwarded: `routes`, `router_mode`, `set_path`, `head`, `style`, `scripts`, `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`.

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

#### Scenario: Accessing style and scripts
- **WHEN** a developer accesses `app.style` or `app.scripts`
- **THEN** the corresponding property values SHALL be returned