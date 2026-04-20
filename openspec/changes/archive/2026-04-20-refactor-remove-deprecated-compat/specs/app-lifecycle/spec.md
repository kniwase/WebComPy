## MODIFIED Requirements

### Requirement: The server entry point shall be a module-level function
Server-side entry points SHALL be module-level functions (`create_asgi_app`, `run_server`) that accept a `WebComPyApp` instance and optional typed config dataclasses. (`create_asgi_app(app, server_config=None)`) This avoids importing server-only dependencies (starlette, uvicorn) in the browser environment. Internally, CLI functions read `AppConfig` from `app.config` and pass `ServerConfig`/`GenerateConfig` as separate arguments; there is no conversion to or from `WebComPyConfig`.

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
- **WHEN** a developer runs `python -m webcompy start` and `webcompy_config.py` defines `app_import_path`
- **THEN** the CLI SHALL discover the app instance via `app_import_path`
- **AND** `webcompy_config.py` SHALL be used for `AppConfig`
- **AND** `webcompy_server_config.py` SHALL be used for `ServerConfig` if present

#### Scenario: Starting a dev server via CLI with --app flag
- **WHEN** a developer runs `python -m webcompy start --app my_app.bootstrap:app`
- **THEN** the CLI SHALL import `my_app.bootstrap` and use the `app` attribute
- **AND** `webcompy_config.py` SHALL NOT be required
- **AND** `webcompy_server_config.py` SHALL still be read if present

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
- **THEN** the CLI SHALL discover the app instance via `webcompy_config.py` or `--app`
- **AND** `generate_config` SHALL be read from `webcompy_server_config.py` if present

### Requirement: WebComPyApp shall forward AppDocumentRoot properties
`WebComPyApp` SHALL provide transparent access to frequently used `AppDocumentRoot` properties. The following properties and methods SHALL be forwarded: `routes`, `router_mode`, `set_path`, `head`, `style`, `scripts`, `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`. The `__component__` property SHALL NOT exist.

#### Scenario: Accessing app routes
- **WHEN** a developer accesses `app.routes`
- **THEN** the route list SHALL be returned (or `None` if no router)

#### Scenario: Setting the path programmatically
- **WHEN** a developer calls `app.set_path("/users/42")`
- **THEN** the router SHALL navigate to `/users/42`

#### Scenario: Accessing head management
- **WHEN** a developer calls `app.set_title("My Page")` or accesses `app.head`
- **THEN** the corresponding head management SHALL work correctly

## REMOVED Requirements

(None — the `__component__` removal is covered in the `app` spec delta)