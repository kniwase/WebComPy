# CLI

## Purpose

The command-line interface bridges the gap between development and deployment. It provides three essential capabilities: a development server for live iteration, a static site generator for production deployment, and project scaffolding for starting new applications. These tools handle the complexity of packaging Python code for browser execution, serving it during development, and producing deployable output — tasks that are unique to a framework that runs Python in the browser.

## Requirements

### Requirement: The dev server shall serve the application with hot-reload
Running `python -m webcompy start --dev` SHALL start a Starlette+uvicorn server that serves the application and automatically reloads the browser when source files change.

#### Scenario: Developing with hot-reload
- **WHEN** a developer runs the dev server and edits a Python file
- **THEN** the browser SHALL detect the change via an SSE connection and reload automatically

### Requirement: The dev server shall serve application packages
The dev server SHALL build a single bundled Python wheel containing both the webcompy framework and the application, and serve it at the `/_webcompy-app-package/` endpoint so that PyScript can load it in the browser.

#### Scenario: Starting the dev server
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the server SHALL build a single bundled wheel containing both webcompy and the application code
- **AND** serve it at `/_webcompy-app-package/{filename}`
- **AND** the browser SHALL be able to import both `webcompy` and the application package

#### Scenario: Dev server with assets
- **WHEN** a developer configures `assets={"logo": "images/logo.png"}` in `WebComPyConfig`
- **THEN** the bundled wheel SHALL include the matching asset files inside the package tree
- **AND** an `_assets_registry.py` module SHALL be generated in the app package mapping `"logo"` to its package path
- **AND** `load_asset("logo")` SHALL return the file content as `bytes`

### Requirement: The generate command shall produce deployable static files
Running `python -m webcompy generate` SHALL produce a complete static site in the `dist/` directory, ready for deployment to any static hosting service.

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

### Requirement: The init command shall scaffold a new project
Running `python -m webcompy init` SHALL create the necessary project structure including a bootstrap file, static directory, and configuration template.

#### Scenario: Scaffolding a new project
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** template files SHALL be copied to the current directory
- **AND** a `static/` directory with `__init__.py` SHALL be created

### Requirement: Application configuration shall be discovered dynamically
The CLI SHALL dynamically import a `webcompy_config` module from the project directory to obtain the `WebComPyConfig` instance, including settings for the app package path, base URL, port, static files, and dependencies.

#### Scenario: Configuring an application
- **WHEN** a developer creates a `webcompy_config.py` with `config = WebComPyConfig(app_package="myapp", base="/app/")`
- **THEN** the CLI SHALL discover and use this configuration
- **AND** the base URL SHALL be normalized to `/app/`

### Requirement: Generated HTML shall include PyScript bootstrapping
Every generated HTML page SHALL include PyScript v2026.3.1 CSS and JS, a loading screen, the app div (either pre-rendered or hidden), and a PyScript configuration specifying all required Python packages. The configuration SHALL reference a single bundled wheel (not separate framework and application wheels) and SHALL NOT include `typing_extensions` as a dependency.

#### Scenario: Inspecting generated HTML
- **WHEN** a generated `index.html` is examined
- **THEN** it SHALL contain a `<script type="module">` tag loading PyScript
- **AND** a `<script type="py">` tag with the bootstrap code
- **AND** a `<style>` tag with scoped component CSS
- **AND** a loading screen div with `id="webcompy-loading"`
- **AND** the PyScript packages list SHALL reference a single bundled wheel URL
- **AND** `typing_extensions` SHALL NOT appear in the packages list

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