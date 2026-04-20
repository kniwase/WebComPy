# CLI

## Purpose

The command-line interface bridges the gap between development and deployment. It provides three essential capabilities: a development server for live iteration, a static site generator for production deployment, and project scaffolding for starting new applications. These tools handle the complexity of packaging Python code for browser execution, serving it during development, and producing deployable output — tasks that are unique to a framework that runs Python in the browser.

## Requirements

### Requirement: The dev server shall serve the application with hot-reload
The development server SHALL be startable via `python -m webcompy start --dev` (existing CLI) or `run_server(app)` (new function). Both SHALL start a Starlette+uvicorn server that serves the application with SSE-based hot-reload. Dev mode is determined by the `--dev` CLI flag, not by a function parameter.

#### Scenario: Starting dev server via CLI (backward compatible)
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL start with hot-reload enabled
- **AND** the behavior SHALL be identical to the current implementation
- **AND** if `WebComPyConfig` is used, a `DeprecationWarning` SHALL be emitted

#### Scenario: Starting dev server via run_server(app)
- **WHEN** a developer calls `run_server(app)` with a `WebComPyApp` instance
- **THEN** the server SHALL start with hot-reload enabled if the `--dev` CLI flag is set
- **AND** `AppConfig` from the app instance SHALL be used instead of `WebComPyConfig`
- **AND** no `webcompy_config.py` file SHALL be required

### Requirement: The dev server shall serve application packages
The dev server SHALL build a single bundled Python wheel containing both the webcompy framework and the application, and serve it at the `/_webcompy-app-package/` endpoint so that PyScript can load it in the browser. The wheel filename SHALL be computed using `get_wheel_filename` from the wheel builder module and SHALL match the URL referenced in the generated HTML.

#### Scenario: Starting the dev server
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL build a single bundled wheel containing both webcompy and the application code
- **AND** serve it at `/_webcompy-app-package/{filename}` where `{filename}` matches the wheel URL in the generated HTML
- **AND** the browser SHALL be able to import both `webcompy` and the application package

#### Scenario: Dev server with assets
- **WHEN** a developer configures `assets={"logo": "images/logo.png"}` in `WebComPyConfig`
- **THEN** the bundled wheel SHALL include the matching asset files inside the package tree
- **AND** an `_assets_registry.py` module SHALL be generated in the app package mapping `"logo"` to its package path
- **AND** `load_asset("logo")` SHALL return the file content as `bytes`

### Requirement: The generate command shall produce deployable static files
Static site generation SHALL be available via `python -m webcompy generate` (existing CLI) or `generate_static_site(app)` (function). Both SHALL produce a complete static site in the configured output directory. The SSG process SHALL enter the app's DI scope for the entire generation pipeline to ensure `inject()` calls during route rendering succeed.

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

#### Scenario: Generating via CLI (backward compatible)
- **WHEN** a developer runs `python -m webcompy generate`
- **THEN** the output SHALL be identical to the current implementation
- **AND** if `WebComPyConfig` is used, a `DeprecationWarning` SHALL be emitted

#### Scenario: Generating via generate_static_site(app)
- **WHEN** a developer calls `generate_static_site(app)` with a `WebComPyApp` instance
- **THEN** a static site SHALL be generated in the `dist` directory
- **AND** all routes, app packages, and static files SHALL be included
- **AND** no `webcompy_config.py` file SHALL be required

### Requirement: The init command shall scaffold a new project
Running `python -m webcompy init` SHALL create the necessary project structure including a bootstrap file, static directory, and configuration template.

#### Scenario: Scaffolding a new project
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** template files SHALL be copied to the current directory
- **AND** a `static/` directory with `__init__.py` SHALL be created

### Requirement: Application configuration shall be discovered dynamically
The CLI SHALL support two configuration discovery patterns: the existing `webcompy_config.py` / `WebComPyConfig` pattern (deprecated) and direct `WebComPyApp` instance with `AppConfig` (preferred). When using the deprecated pattern, a `DeprecationWarning` SHALL be emitted. Internally, `AppConfig` is converted to `WebComPyConfig` for compatibility with existing HTML generation and wheel-building code; this conversion is an implementation detail not exposed to developers.

#### Scenario: Using the new AppConfig pattern
- **WHEN** a developer creates `WebComPyApp(root_component=Root, config=AppConfig(base_url="/app/"))`
- **THEN** the CLI SHALL use the provided `AppConfig`
- **AND** no `webcompy_config.py` SHALL be required

#### Scenario: Using the deprecated WebComPyConfig pattern
- **WHEN** a developer provides `webcompy_config.py` with `WebComPyConfig`
- **THEN** the CLI SHALL discover and use this configuration
- **AND** a `DeprecationWarning` SHALL be emitted
- **AND** the application SHALL still function correctly

### Requirement: Generated HTML shall include PyScript bootstrapping
Every generated HTML page SHALL include PyScript v2026.3.1 CSS and JS, a loading screen, the app div (either pre-rendered or hidden), and a PyScript configuration specifying all required Python packages. The configuration SHALL reference a single bundled wheel (not separate framework and application wheels) and SHALL NOT include `typing_extensions` as a dependency. The bundled wheel URL SHALL be computed using `get_wheel_filename` from the wheel builder module, using the actual app package name — not a hardcoded `"app"` prefix.

#### Scenario: Inspecting generated HTML
- **WHEN** a generated `index.html` is examined for an app package named `myapp`
- **THEN** it SHALL contain a `<script type="module">` tag loading PyScript
- **AND** a `<script type="py">` tag with the bootstrap code
- **AND** a `<style>` tag with scoped component CSS
- **AND** a loading screen div with `id="webcompy-loading"`
- **AND** the PyScript packages list SHALL reference a single bundled wheel URL using `get_wheel_filename("myapp", version)`
- **AND** `typing_extensions` SHALL NOT appear in the packages list

### Requirement: WebComPyConfig shall emit DeprecationWarning
`WebComPyConfig` SHALL emit a `DeprecationWarning` when instantiated, directing developers to use `AppConfig` instead.

#### Scenario: Creating a WebComPyConfig instance
- **WHEN** a developer creates `WebComPyConfig(app_package="myapp")`
- **THEN** a `DeprecationWarning` SHALL be emitted
- **AND** the configuration SHALL still function correctly for backward compatibility

### Requirement: Application configuration shall support assets
`WebComPyConfig` SHALL accept an `assets` parameter that maps string keys to file paths relative to the app package directory. These assets SHALL be included in the bundled wheel and accessible at runtime via `load_asset`.

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