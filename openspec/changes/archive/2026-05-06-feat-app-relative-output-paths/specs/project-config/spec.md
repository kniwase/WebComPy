## ADDED Requirements

### Requirement: dist and static_files_dir shall be resolved relative to the app package directory
The `dist` and `static_files_dir` values in `GenerateConfig` SHALL be resolved relative to `app_package_path` (the resolved absolute path of `AppConfig.app_package`). When the value is an absolute path, it SHALL be used as-is. When relative, it SHALL be joined with `app_package_path` and then resolved to an absolute path.

#### Scenario: Relative dist resolved against app_package_path
- **WHEN** `AppConfig(app_package="my_app")` and `GenerateConfig(dist="dist")`
- **THEN** static site output SHALL be written to `<app_package_path>/dist/`

#### Scenario: Relative static_files_dir resolved against app_package_path
- **WHEN** `AppConfig(app_package="my_app")` and `GenerateConfig(static_files_dir="static")`
- **THEN** static files SHALL be read from `<app_package_path>/static/`

#### Scenario: Absolute dist path bypasses app_package_path
- **WHEN** `AppConfig(app_package="my_app")` and `GenerateConfig(dist="/tmp/out")`
- **THEN** static site output SHALL be written to `/tmp/out/`

#### Scenario: Default app_package resolves to CWD
- **WHEN** `AppConfig()` with default `app_package="."` and `GenerateConfig(dist="dist")`
- **THEN** `app_package_path` SHALL equal the project root (CWD)
- **AND** static site output SHALL be written to `./dist/` (unchanged from previous behavior)

### Requirement: static_files_dir_path property shall be removed from ServerConfig and GenerateConfig
`ServerConfig` and `GenerateConfig` SHALL NOT expose a `static_files_dir_path` property. Path resolution of `static_files_dir` SHALL occur at the call sites (`_generate.py` and `_server.py`) where `app_package_path` is available. The `static_files_dir` string field SHALL remain as the user-facing configuration value.

#### Scenario: static_files_dir is resolved in generate context
- **WHEN** `generate_static_site()` runs
- **THEN** `static_files_dir` SHALL be resolved as `(app.config.app_package_path / generate_config.static_files_dir).absolute()`

#### Scenario: static_files_dir is resolved in server context
- **WHEN** `create_asgi_app()` runs
- **THEN** `static_files_dir` SHALL be resolved as `(app.config.app_package_path / server_config.static_files_dir).absolute()`

## MODIFIED Requirements

### Requirement: CLI flags shall override config file values
CLI flags (`--dev`, `--port`, `--dist`) SHALL override values from `webcompy_server_config.py` and the defaults. When a flag is provided, it takes precedence; when not provided, the config file value or default is used. The `--dist` CLI flag SHALL accept CWD-relative or absolute paths and SHALL bypass `app_package_path`-relative resolution.

#### Scenario: Overriding port with --port
- **WHEN** `webcompy_server_config.py` sets `server_config = ServerConfig(port=8080)`
- **AND** a developer runs `python -m webcompy start --port 3000`
- **THEN** the server SHALL start on port 3000

#### Scenario: Overriding dist with --dist forces CWD-relative path
- **WHEN** `webcompy_server_config.py` sets `generate_config = GenerateConfig(dist="dist")`
- **AND** a developer runs `python -m webcompy generate --dist out`
- **THEN** static files SHALL be generated in the CWD-relative `out` directory (bypassing `app_package_path`-relative resolution)

#### Scenario: Overriding dev mode with --dev
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** hot-reload SHALL be enabled regardless of `ServerConfig.dev` value

#### Scenario: No overrides
- **WHEN** a developer runs `python -m webcompy start` without flags
- **AND** `webcompy_server_config.py` sets `server_config = ServerConfig(port=8080)`
- **THEN** the server SHALL start on port 8080
