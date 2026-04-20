# Project Configuration

## Purpose

Project configuration separates browser-relevant app settings from server-side-only settings using two configuration files. `webcompy_config.py` contains settings shared between browser and server environments (including the app import path for CLI discovery), while `webcompy_server_config.py` contains settings only needed for development, serving, and static site generation. This separation ensures that browser code never imports server-only dependencies and allows CLI tools to discover the application without mandatory `--app` flags.

## Requirements

### Requirement: Project configuration shall use a two-file pattern
The project SHALL use two configuration files: `webcompy_config.py` for app-shared settings and `webcompy_server_config.py` for server-only settings. `webcompy_config.py` SHALL contain `app_import_path` (a string in `"module.path:variable_name"` format) and `app_config` (an `AppConfig` instance). `webcompy_server_config.py` SHALL contain `server_config` (a `ServerConfig` instance) and `generate_config` (a `GenerateConfig` instance).

#### Scenario: Creating a minimal project configuration
- **WHEN** a developer creates `webcompy_config.py` with `app_import_path = "my_app.bootstrap:app"` and `app_config = AppConfig(app_package="my_app")`
- **THEN** the CLI SHALL be able to discover the app without `--app`
- **AND** `bootstrap.py` SHALL be able to import `app_config` from `webcompy_config`

#### Scenario: Creating a server configuration
- **WHEN** a developer creates `webcompy_server_config.py` with `server_config = ServerConfig(port=8080)` and `generate_config = GenerateConfig(dist="dist")`
- **THEN** `run_server()` SHALL use `server_config.port` as the default port
- **AND** `generate_static_site()` SHALL use `generate_config.dist` as the default output directory

#### Scenario: Omitting server configuration
- **WHEN** a developer does not create `webcompy_server_config.py`
- **THEN** `ServerConfig()` defaults SHALL be used for serving
- **AND** `GenerateConfig()` defaults SHALL be used for SSG
- **AND** the application SHALL function correctly

### Requirement: CLI shall discover the app via app_import_path
The CLI SHALL discover the `WebComPyApp` instance by first checking the `--app` CLI flag, then falling back to `webcompy_config.py`'s `app_import_path`. The `app_import_path` SHALL follow the `"module.path:variable_name"` format. The `discover_app` function in `webcompy.cli` SHALL be the programmatic interface for this discovery, accepting an optional `app_import_path` string parameter.

#### Scenario: Discovery via --app flag
- **WHEN** a developer runs `python -m webcompy start --app my_app.bootstrap:app`
- **THEN** the CLI SHALL import `my_app.bootstrap` and get the `app` attribute
- **AND** `webcompy_config.py` SHALL NOT be required

#### Scenario: Discovery via webcompy_config.py
- **WHEN** a developer runs `python -m webcompy start` without `--app`
- **AND** `webcompy_config.py` exists with `app_import_path = "my_app.bootstrap:app"`
- **THEN** the CLI SHALL import `my_app.bootstrap` and get the `app` attribute

#### Scenario: No app_import_path and no --app flag
- **WHEN** a developer runs `python -m webcompy start` without `--app`
- **AND** no `webcompy_config.py` exists or it has no `app_import_path`
- **THEN** a clear error SHALL be raised indicating that either `--app` or `webcompy_config.py` with `app_import_path` is required

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

#### Scenario: No overrides
- **WHEN** a developer runs `python -m webcompy start` without flags
- **AND** `webcompy_server_config.py` sets `server_config = ServerConfig(port=8080)`
- **THEN** the server SHALL start on port 8080

### Requirement: Project scaffolding shall generate two config files
`python -m webcompy init` SHALL generate both `webcompy_config.py` (with `app_import_path` and `app_config`) and `webcompy_server_config.py` (with `server_config` and `generate_config`).

#### Scenario: Running webcompy init
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** `webcompy_config.py` SHALL be created with `app_import_path` and `app_config`
- **AND** `webcompy_server_config.py` SHALL be created with `server_config` and `generate_config`
- **AND** `bootstrap.py` SHALL import `app_config` from `webcompy_config`
- **AND** the project SHALL be immediately runnable via `python -m webcompy start`