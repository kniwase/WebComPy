## MODIFIED Requirements

### Requirement: Project configuration shall use a single config file
The project SHALL use a single configuration file: `webcompy_config.py`. This file SHALL contain `config = WebComPyBuildConfig(app_module, ...)` with all build and server settings. The former `webcompy_server_config.py` is removed. `WebComPyBuildConfig` is imported from `webcompy.cli.config`. The app module SHALL be imported via `import my_app.app as app_module` (not `from my_app.app import app`, as the latter returns the instance, losing access to `__file__`). The app entry point file SHALL be named `app.py` (formerly `bootstrap.py`).

#### Scenario: Creating a project configuration
- **WHEN** a developer creates `webcompy_config.py` at the project root with:
  ```python
  import my_app.app as app_module
  from webcompy.cli.config import WebComPyBuildConfig, WebComPyServerConfig

  config = WebComPyBuildConfig(
      app_module,
      dependencies=None,
      dependencies_from="browser",
      server=WebComPyServerConfig(port=8080),
  )
  ```
- **THEN** the CLI SHALL be able to discover the app and config without `--config`
- **AND** `app.py` SHALL be the app entry point (not `bootstrap.py`)

#### Scenario: Creating a project configuration inside the app package
- **WHEN** a developer creates `webcompy_config.py` inside the `my_app/` package
- **AND** runs `python -m webcompy start --config my_app/webcompy_config.py`
- **THEN** the CLI SHALL discover the app via the config

#### Scenario: Omitting server configuration
- **WHEN** a developer creates `WebComPyBuildConfig(app)` without `server`
- **THEN** `WebComPyServerConfig()` defaults SHALL be used (`port=8080`, `dev=False`)

### Requirement: CLI shall discover the app via --config or webcompy_config.py
The CLI SHALL discover the `WebComPyApp` instance and build configuration by first checking the `--config` CLI flag, then falling back to `webcompy_config.py` in the current working directory. The `--app` flag is removed. The `--config` flag accepts a file path to a Python module containing a `config` attribute of type `WebComPyBuildConfig`.

#### Scenario: Discovery via --config flag
- **WHEN** a developer runs `python -m webcompy start --config my_config.py`
- **THEN** the CLI SHALL import `my_config.py` and get the `config` attribute
- **AND** `config.app` SHALL be the `WebComPyApp` instance
- **AND** `config.server` SHALL be the `WebComPyServerConfig` instance

#### Scenario: Discovery via root-level webcompy_config.py
- **WHEN** a developer runs `python -m webcompy start` without `--config`
- **AND** `webcompy_config.py` exists at the project root
- **THEN** the CLI SHALL import `webcompy_config.py` and get the `config` attribute

#### Scenario: No config file and no --config flag
- **WHEN** a developer runs `python -m webcompy start` without `--config`
- **AND** no `webcompy_config.py` exists at the project root
- **THEN** a clear error SHALL be raised indicating that `--config` or `webcompy_config.py` is required

### Requirement: CLI flags shall override config file values
CLI flags SHALL override values from `WebComPyBuildConfig` and `WebComPyServerConfig`. When a flag is provided, it takes precedence; when not provided, the config value or default is used.

#### Scenario: Overriding dev mode with --dev
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** hot-reload SHALL be enabled regardless of `WebComPyServerConfig.dev` value

#### Scenario: Overriding dist with --dist
- **WHEN** a developer runs `python -m webcompy generate --dist out`
- **THEN** static files SHALL be generated in the `out` directory (bypassing `WebComPyBuildConfig.dist`)

### Requirement: Project scaffolding shall generate single config file and app.py
`python -m webcompy init` SHALL generate a single `webcompy_config.py` at the project root with `config = WebComPyBuildConfig(...)` and an `app.py` file (not `bootstrap.py`).

#### Scenario: Running webcompy init
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** `webcompy_config.py` SHALL be created at the project root with `config = WebComPyBuildConfig(app, ...)`
- **AND** `app.py` SHALL be created (not `bootstrap.py`)
- **AND** the project SHALL be immediately runnable via `python -m webcompy start`

## REMOVED Requirements

### Requirement: Project configuration shall use a two-file pattern
**Reason**: Consolidated into a single `webcompy_config.py` with `WebComPyBuildConfig`.
**Migration**: Merge `webcompy_server_config.py` contents into `webcompy_config.py`. Remove `webcompy_server_config.py`.

### Requirement: CLI shall discover the app via app_import_path
**Reason**: Replaced by `WebComPyBuildConfig.app` which holds the app instance directly. The `--app` flag is replaced by `--config`.
**Migration**: Use `--config path/to/webcompy_config.py` instead of `--app my_app.bootstrap:app`.