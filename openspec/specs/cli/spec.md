# CLI

## Purpose

The command-line interface bridges the gap between development and deployment. It provides three essential capabilities: a development server for live iteration, a static site generator for production deployment, and project scaffolding for starting new applications. These tools handle the complexity of packaging Python code for browser execution, serving it during development, and producing deployable output — tasks that are unique to a framework that runs Python in the browser.

## Requirements

### Requirement: The dev server shall serve the application with hot-reload
The development server SHALL be startable via `python -m webcompy start --dev` or `run_server(app)`. Both SHALL start a Starlette+uvicorn server that serves the application with SSE-based hot-reload. Dev mode is determined by `ServerConfig.dev` or the `--dev` CLI flag (which overrides the config file value).

#### Scenario: Starting dev server via CLI
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL start with hot-reload enabled
- **AND** `ServerConfig.dev` SHALL be overridden to `True`

#### Scenario: Starting dev server via run_server(app)
- **WHEN** a developer calls `run_server(app)` with a `WebComPyApp` instance
- **THEN** the server SHALL start with hot-reload enabled if the `--dev` CLI flag is set
- **AND** `AppConfig` from the app instance SHALL be used

#### Scenario: Starting dev server with custom port
- **WHEN** a developer runs `python -m webcompy start --port 3000`
- **THEN** the server SHALL start on port 3000
- **AND** the `--port` flag SHALL override `ServerConfig.port`

### Requirement: The dev server shall serve application packages
The dev server SHALL build two separate Python wheels: a browser-only webcompy framework wheel and an application wheel containing the app code and bundled pure-Python dependencies. Both wheels SHALL be served at stable `/_webcompy-app-package/` endpoints. The framework wheel SHALL have `Cache-Control: max-age=86400, must-revalidate` and the app wheel in dev mode SHALL have `Cache-Control: no-cache`.

#### Scenario: Starting the dev server
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL build a single bundled wheel containing both webcompy and the application code
- **AND** serve it at `/_webcompy-app-package/{filename}` where `{filename}` matches the wheel URL in the generated HTML
- **AND** the browser SHALL be able to import both `webcompy` and the application package

#### Scenario: Dev server with assets
- **WHEN** a developer configures `assets={"logo": "images/logo.png"}` in `AppConfig`
- **THEN** the bundled wheel SHALL include the matching asset files inside the package tree
- **AND** an `_assets_registry.py` module SHALL be generated in the app package mapping `"logo"` to its package path
- **AND** `load_asset("logo")` SHALL return the file content as `bytes`

### Requirement: The generate command shall produce deployable static files
Static site generation SHALL be available via `python -m webcompy generate` or `generate_static_site(app, generate_config=None)`. Both SHALL produce a complete static site in the configured output directory. The SSG process SHALL enter the app's DI scope for the entire generation pipeline to ensure `inject()` calls during route rendering succeed.

#### Scenario: Generating a multi-page application with history mode
- **WHEN** routes are defined with history mode
- **THEN** an `index.html` SHALL be generated for each route path
- **AND** a `404.html` SHALL be generated for unmatched paths
- **AND** a single bundled wheel SHALL be placed in `dist/_webcompy-app-package/`
- **AND** static files SHALL be copied from the configured directory
- **AND** a `.nojekyll` file SHALL be created for GitHub Pages compatibility

#### Scenario: Generating a single-page application with hash mode
- **WHEN** no router or hash mode is used
- **THEN** a single `index.html` SHALL be generated at the dist root
- **AND** all other assets SHALL be included as in the history mode case

#### Scenario: Generating with custom dist via --dist flag
- **WHEN** a developer runs `python -m webcompy generate --dist out`
- **THEN** static files SHALL be generated in the `out` directory
- **AND** the `--dist` flag SHALL override `GenerateConfig.dist`

#### Scenario: Generating via generate_static_site(app)
- **WHEN** a developer calls `generate_static_site(app)` with a `WebComPyApp` instance
- **THEN** a static site SHALL be generated in the `dist` directory
- **AND** all routes, app packages, and static files SHALL be included

### Requirement: The init command shall scaffold a new project
Running `python -m webcompy init` SHALL create the necessary project structure including a bootstrap file, static directory, and two configuration files (`webcompy_config.py` and `webcompy_server_config.py`).

#### Scenario: Scaffolding a new project
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** template files SHALL be copied to the current directory
- **AND** a `static/` directory with `__init__.py` SHALL be created
- **AND** `webcompy_config.py` SHALL be created with `app_import_path` and `app_config`
- **AND** `webcompy_server_config.py` SHALL be created with `server_config` and `generate_config`

### Requirement: Application configuration shall be discovered via two-file pattern
The CLI SHALL discover the app instance using `webcompy_config.py` (which contains `app_import_path` and `app_config`) or the `--app` CLI flag. Configuration files can be placed at the project root or inside the app package directory. When `--app` is provided, the CLI derives the package from the import path and searches for `webcompy_server_config.py` in that package first, then falls back to the project root. The `webcompy_server_config.py` file is optional and contains server/SSG-only settings (`server_config`, `generate_config`). The `discover_app` function SHALL be the public API for programmatic app discovery, exported from `webcompy.cli`. It SHALL return a tuple of `(WebComPyApp, str | None)` where the second element is the derived package name.

#### Scenario: Discovery via --app flag
- **WHEN** a developer runs `python -m webcompy start --app my_app.bootstrap:app`
- **THEN** the CLI SHALL import `my_app.bootstrap` and use the `app` attribute
- **AND** the CLI SHALL derive the package as `"my_app"`
- **AND** `webcompy_config.py` SHALL NOT be required
- **AND** `webcompy_server_config.py` SHALL be searched first as `my_app.webcompy_server_config`, then as root-level `webcompy_server_config`

#### Scenario: Discovery via root-level webcompy_config.py
- **WHEN** a developer runs `python -m webcompy start` without `--app`
- **AND** `webcompy_config.py` exists at the project root with `app_import_path = "my_app.bootstrap:app"`
- **THEN** the CLI SHALL import `my_app.bootstrap` and get the `app` attribute

#### Scenario: No app_import_path and no --app flag
- **WHEN** a developer runs `python -m webcompy start` without `--app`
- **AND** no `webcompy_config.py` exists at the project root or it has no `app_import_path`
- **THEN** a clear error SHALL be raised indicating that either `--app` or `webcompy_config.py` with `app_import_path` is required

### Requirement: Generated HTML shall include PyScript bootstrapping
Every generated HTML page SHALL include PyScript v2026.3.1 CSS and JS, a loading screen, the app div (either pre-rendered or hidden), and a PyScript configuration specifying all required Python packages. The configuration SHALL reference a single bundled wheel (not separate framework and application wheels) and SHALL NOT include `typing_extensions` as a dependency. The bundled wheel URL SHALL be computed using `get_wheel_filename` from the wheel builder module, using the actual app package name — not a hardcoded `"app"` prefix. When `AppConfig.profile=True`, the generated `<script type="py">` tag SHALL include inline profiling code that captures `pyscript_ready` at the start of PyScript execution and passes it to the app instance before `app.run()`.

#### Scenario: Inspecting generated HTML
- **WHEN** a generated `index.html` is examined for an app package named `myapp`
- **THEN** it SHALL contain a `<script type="module">` tag loading PyScript
- **AND** a `<script type="py">` tag with the bootstrap code
- **AND** a `<style>` tag with scoped component CSS
- **AND** a loading screen div with `id="webcompy-loading"`
- **AND** the PyScript packages list SHALL reference a single bundled wheel URL using `get_wheel_filename("myapp", version)`
- **AND** `typing_extensions` SHALL NOT appear in the packages list

#### Scenario: Inspecting generated HTML with profiling enabled
- **WHEN** `AppConfig.profile=True` and a generated `index.html` is examined
- **THEN** the `<script type="py">` tag SHALL start with `import time` and `_pyscript_ready = time.perf_counter()`
- **AND** after the app import, `app._profile_data["pyscript_ready"] = _pyscript_ready` SHALL be present
- **AND** `app.run()` SHALL follow

#### Scenario: Inspecting generated HTML with profiling disabled
- **WHEN** `AppConfig.profile=False` (default) and a generated `index.html` is examined
- **THEN** the `<script type="py">` tag SHALL contain only the standard bootstrap (`from <app>.bootstrap import app; app.run()`)
- **AND** no profiling code SHALL appear

### Requirement: CLI flags shall override config file values
CLI flags (`--dev`, `--port`, `--dist`) SHALL override values from `webcompy_server_config.py` and the defaults. When a flag is provided, it takes precedence; when not provided, the config file value or default is used.

#### Scenario: Overriding port with --port
- **WHEN** `webcompy_server_config.py` sets `server_config = ServerConfig(port=8080)`
- **AND** a developer runs `python -m webcompy start --port 3000`
- **THEN** the server SHALL start on port 3000

#### Scenario: Overriding dist with --dist
- **WHEN** `webcompy_server_config.py` sets `generate_config = GenerateConfig(dist="dist")`
- **AND** a developer runs `python -m webcompy generate --dist out`
- **THEN** static files SHALL be generated in the `out` directory

#### Scenario: Overriding dev mode with --dev
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** hot-reload SHALL be enabled regardless of `ServerConfig.dev` value

### Requirement: Application configuration shall support assets
`AppConfig` SHALL accept an `assets` parameter that maps string keys to file paths relative to the app package directory. These assets SHALL be included in the bundled wheel and accessible at runtime via `load_asset`.

#### Scenario: Configuring assets for application resources
- **WHEN** a developer specifies `assets={"logo": "images/logo.png", "config": "data/settings.json"}`
- **THEN** the CLI SHALL include the referenced files in the bundled wheel inside the app package tree
- **AND** an `_assets_registry.py` module SHALL be generated mapping `"logo"` to `"app/images/logo.png"` and `"config"` to `"app/data/settings.json"`
- **AND** those files SHALL be accessible via `load_asset("logo")` and `load_asset("config")` in the browser environment

#### Scenario: Omitting assets
- **WHEN** a developer does not specify `assets`
- **THEN** only Python source files, stub files, and `py.typed` markers SHALL be included in the wheel
- **AND** no `_assets_registry.py` module SHALL be generated

### Requirement: Assets shall be loadable by key at runtime
The `webcompy.assets` module SHALL provide a `load_asset(key: str) -> bytes` function and an `AssetNotFoundError` exception. When called, `load_asset` SHALL look up the key in the app's `_assets_registry` module and return the file content as `bytes` using `importlib.resources`.

#### Scenario: Loading an asset by key
- **WHEN** `load_asset("logo")` is called in browser code where `_assets_registry` maps `"logo"` to `"app/images/logo.png"`
- **THEN** the function SHALL return the raw `bytes` content of `app/images/logo.png`

#### Scenario: Asset key not found
- **WHEN** `load_asset("nonexistent")` is called
- **THEN** `AssetNotFoundError` SHALL be raised with the key as an attribute

#### Scenario: No assets registry module
- **WHEN** `load_asset` is called but the `app._assets_registry` module cannot be imported
- **THEN** `AssetNotFoundError` SHALL be raised