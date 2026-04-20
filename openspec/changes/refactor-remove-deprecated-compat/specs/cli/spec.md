## MODIFIED Requirements

### Requirement: The project structure shall be discoverable by convention
A WebComPy project SHALL follow a specific directory layout. The CLI SHALL discover the app instance using `webcompy_config.py` (which contains `app_import_path` and `app_config`) or the `--app` CLI flag. The `webcompy_server_config.py` file is optional and contains server/SSG-only settings (`server_config`, `generate_config`). The legacy `WebComPyConfig` pattern SHALL NOT be supported.

#### Scenario: Starting the dev server with app_import_path
- **WHEN** a developer runs `python -m webcompy start` and `webcompy_config.py` defines `app_import_path = "my_app.bootstrap:app"`
- **THEN** the CLI SHALL discover the app instance
- **AND** `AppConfig` from `app.config` SHALL be used
- **AND** `ServerConfig` from `webcompy_server_config.py` SHALL be used if present

#### Scenario: Starting the dev server with --app flag
- **WHEN** a developer runs `python -m webcompy start --app my_app.bootstrap:app`
- **THEN** the CLI SHALL import `my_app.bootstrap:app`
- **AND** `webcompy_config.py` SHALL NOT be required
- **AND** `webcompy_server_config.py` SHALL still be read if present

#### Scenario: Minimal project structure
- **WHEN** a project contains `webcompy_config.py` with `app_import_path` and `my_app/bootstrap.py`
- **THEN** the CLI SHALL be able to start the dev server and generate static output
- **AND** no `webcompy_server_config.py` is required (defaults are used)

### Requirement: The CLI shall provide three distinct workflows
The framework SHALL provide three commands serving different phases of the development lifecycle: `start` for live development with hot-reload, `generate` for production static site generation, and `init` for project scaffolding. All three SHALL use the new two-file configuration pattern.

#### Scenario: Developing with hot-reload
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** a local server SHALL start with SSE-based hot-reload
- **AND** changes to Python source files SHALL trigger a browser refresh
- **AND** `ServerConfig.dev` SHALL be overridden to `True`

#### Scenario: Generating a production build
- **WHEN** a developer runs `python -m webcompy generate`
- **THEN** a `dist/` directory SHALL be created with pre-rendered HTML for each route
- **AND** Python wheel packages SHALL be included for browser-side execution
- **AND** the output SHALL be deployable to any static hosting service

#### Scenario: Starting a new project
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** a complete project structure SHALL be created with a working example application
- **AND** `webcompy_config.py` SHALL be created with `app_import_path` and `app_config`
- **AND** `webcompy_server_config.py` SHALL be created with `server_config` and `generate_config`
- **AND** the developer SHALL be able to immediately run the dev server

## REMOVED Requirements

### Requirement: Application configuration shall be discovered dynamically (legacy WebComPyConfig pattern)
**Reason**: Replaced by the two-file configuration pattern (`webcompy_config.py` + `webcompy_server_config.py`). The `WebComPyConfig` class and its discovery mechanism are removed.
**Migration**: Replace `webcompy_config.py` containing `WebComPyConfig(app_package=..., base=..., ...)` with two files: `webcompy_config.py` containing `app_import_path` and `app_config = AppConfig(...)`, and `webcompy_server_config.py` containing `server_config = ServerConfig(...)` and `generate_config = GenerateConfig(...)`.

### Requirement: WebComPyConfig shall emit DeprecationWarning
**Reason**: `WebComPyConfig` class is removed entirely. No deprecation path needed.
**Migration**: Use `AppConfig` in `webcompy_config.py` instead.