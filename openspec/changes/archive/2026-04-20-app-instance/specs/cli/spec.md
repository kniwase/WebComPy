## MODIFIED Requirements

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

### Requirement: The generate command shall produce deployable static files
Static site generation SHALL be available via `python -m webcompy generate` (existing CLI) or `generate_static_site(app)` (function). Both SHALL produce a complete static site in the configured output directory. The SSG process SHALL enter the app's DI scope for the entire generation pipeline to ensure `inject()` calls during route rendering succeed.

#### Scenario: Generating via CLI (backward compatible)
- **WHEN** a developer runs `python -m webcompy generate`
- **THEN** the output SHALL be identical to the current implementation
- **AND** if `WebComPyConfig` is used, a `DeprecationWarning` SHALL be emitted

#### Scenario: Generating via generate_static_site(app)
- **WHEN** a developer calls `generate_static_site(app)` with a `WebComPyApp` instance
- **THEN** a static site SHALL be generated in the `dist` directory
- **AND** all routes, app packages, and static files SHALL be included
- **AND** no `webcompy_config.py` file SHALL be required

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

## ADDED Requirements

### Requirement: WebComPyConfig shall emit DeprecationWarning
`WebComPyConfig` SHALL emit a `DeprecationWarning` when instantiated, directing developers to use `AppConfig` instead.

#### Scenario: Creating a WebComPyConfig instance
- **WHEN** a developer creates `WebComPyConfig(app_package="myapp")`
- **THEN** a `DeprecationWarning` SHALL be emitted
- **AND** the configuration SHALL still function correctly for backward compatibility