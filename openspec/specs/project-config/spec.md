# Project Configuration

## Purpose

Project configuration uses a single configuration file (`webcompy_config.py`) containing a `WebComPyBuildConfig` instance that holds all build-time and server settings. This consolidates the former two-file pattern (`webcompy_config.py` and `webcompy_server_config.py`) into one file, and replaces the `app_import_path` string with a direct module import pattern. The app entry point file is named `app.py` (formerly `bootstrap.py`).

In the refactored package structure, `webcompy_config.py` imports from `webcompy_cli.config` (the canonical import path) instead of `webcompy.cli.config`. Legacy import shims exist for backward compatibility during the transition period.

## Requirements

### MODIFIED: Project configuration shall use a single config file
The project SHALL use a single configuration file: `webcompy_config.py`. This file SHALL contain `config = WebComPyBuildConfig(app_module, ...)` with all build and server settings. The former `webcompy_server_config.py` is removed. `WebComPyBuildConfig` is imported from `webcompy_cli.config` (legacy shim `webcompy.cli.config` also works). The app module SHALL be imported via `import my_app.app as app_module` (not `from my_app.app import app`, as the latter returns the instance, losing access to `__file__`). The app entry point file SHALL be named `app.py` (formerly `bootstrap.py`).

#### Scenario: Creating a project configuration
- **WHEN** a developer creates `webcompy_config.py` at the project root with:
  ```python
  import my_app.app as app_module
  from webcompy_cli.config import WebComPyBuildConfig, WebComPyServerConfig

  config = WebComPyBuildConfig(
      app_module,
      dependencies=None,
      dependencies_from="browser",
      server=WebComPyServerConfig(port=8080),
  )
  ```
- **THEN** the CLI SHALL be able to discover the app and config without `--config`
- **AND** `app.py` SHALL be the app entry point (not `bootstrap.py`)

#### Scenario: Creating a project configuration with legacy import path
- **WHEN** a developer creates `webcompy_config.py` with `from webcompy.cli.config import WebComPyBuildConfig, WebComPyServerConfig`
- **THEN** the import SHALL succeed via the legacy shim
- **AND** the CLI SHALL discover the app identically

#### Scenario: Creating a project configuration inside the app package
- **WHEN** a developer creates `webcompy_config.py` inside the `my_app/` package
- **AND** runs `python -m webcompy start --config my_app/webcompy_config.py`
- **THEN** the CLI SHALL discover the app via the config

#### Scenario: Omitting server configuration
- **WHEN** a developer creates `WebComPyBuildConfig(app)` without `server`
- **THEN** `WebComPyServerConfig()` defaults SHALL be used (`port=8080`, `dev=False`)

### MODIFIED: CLI shall discover the app via --config or webcompy_config.py
The CLI SHALL discover the `WebComPyApp` instance and build configuration by first checking the `--config` CLI flag, then falling back to `webcompy_config.py` in the current working directory. The `--app` flag is removed. The `--config` flag accepts a Python import path string (e.g., `"my_project.webcompy_config"`). The config module's parent directory must be on `sys.path`. The default CWD-based discovery works because CWD is on `sys.path`.

#### Scenario: Discovery via --config flag
- **WHEN** a developer runs `python -m webcompy start --config path.to.my_config`
- **THEN** the CLI SHALL import `path.to.my_config` and get the `config` attribute
- **AND** `config.app` SHALL be the computed `WebComPyApp` instance
- **AND** `config.app_package_path` SHALL be derived from `config.app_module.__file__`
- **AND** `config.server` SHALL provide server settings

#### Scenario: Discovery via root-level webcompy_config.py
- **WHEN** a developer runs `python -m webcompy start` without `--config`
- **AND** `webcompy_config.py` exists at the project root with `config = WebComPyBuildConfig(app, ...)`
- **THEN** the CLI SHALL import `webcompy_config` and get the `config` attribute

#### Scenario: No config file and no --config flag
- **WHEN** a developer runs `python -m webcompy start` without `--config`
- **AND** no `webcompy_config.py` exists at the project root
- **THEN** a clear error SHALL be raised indicating that `--config` flag or `webcompy_config.py` is required

### MODIFIED: CLI flags shall override config file values
CLI flags SHALL override values from `WebComPyBuildConfig` and `WebComPyServerConfig`. When a flag is provided, it takes precedence; when not provided, the config value or default is used.

#### Scenario: Overriding dev mode with --dev
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** hot-reload SHALL be enabled regardless of `WebComPyServerConfig.dev` value

#### Scenario: Overriding dist with --dist
- **WHEN** a developer runs `python -m webcompy generate --dist out`
- **THEN** static files SHALL be generated in the `out` directory (bypassing `WebComPyBuildConfig.dist`)

### MODIFIED: Project scaffolding shall generate single config file and app.py
`python -m webcompy init` SHALL generate a single `webcompy_config.py` at the project root with `config = WebComPyBuildConfig(...)` and an `app.py` file (not `bootstrap.py`).

#### Scenario: Running webcompy init
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** `webcompy_config.py` SHALL be created at the project root with `config = WebComPyBuildConfig(app, ...)`
- **AND** `app.py` SHALL be created (not `bootstrap.py`)
- **AND** the project SHALL be immediately runnable via `python -m webcompy start`

### MODIFIED: dist and static_files_dir shall be resolved relative to the app package directory
The `dist` and `static_files_dir` values in `WebComPyBuildConfig` SHALL be resolved relative to `app_package_path` (the resolved path from `Path(app_module.__file__).parent`). When the value is an absolute path, it SHALL be used as-is. When relative, it SHALL be joined with `app_package_path` and then resolved to an absolute path.

#### Scenario: Relative dist resolved against app_package_path
- **WHEN** `WebComPyBuildConfig(app_module)` with `dist="dist"`
- **THEN** static site output SHALL be written to `<app_package_path>/dist/`

#### Scenario: Relative static_files_dir resolved against app_package_path
- **WHEN** `WebComPyBuildConfig(app_module)` with `static_files_dir="static"`
- **THEN** static files SHALL be read from `<app_package_path>/static/`

#### Scenario: Absolute dist path bypasses app_package_path
- **WHEN** `WebComPyBuildConfig(app_module)` with `dist="/tmp/out"`
- **THEN** static site output SHALL be written to `/tmp/out/`

### MODIFIED: LockfileSyncConfig shall configure lock file sync behavior
`WebComPyBuildConfig` SHALL support an optional `lockfile_sync_config` field of type `LockfileSyncConfig`. This dataclass configures how `webcompy lock --export`, `--sync`, and `--install` discover and interact with project dependency files. `LockfileSyncConfig` is importable from `webcompy_cli.config` (legacy shim `webcompy.cli.config` also works).

#### Scenario: Creating a LockfileSyncConfig with explicit requirements_path
- **WHEN** a developer creates `WebComPyBuildConfig(app_module, lockfile_sync_config=LockfileSyncConfig(requirements_path="../requirements.txt"))`
- **THEN** `webcompy lock --export` SHALL use the specified path instead of auto-discovery
- **AND** the path SHALL be resolved relative to `app_package_path`

#### Scenario: Creating a LockfileSyncConfig with sync_group
- **WHEN** a developer creates `WebComPyBuildConfig(app_module, lockfile_sync_config=LockfileSyncConfig(sync_group="browser"))`
- **THEN** `webcompy lock --sync` SHALL compare `[project.optional-dependencies.browser]` from `pyproject.toml` instead of `[project.dependencies]`

#### Scenario: Omitting LockfileSyncConfig
- **WHEN** a developer does not include `lockfile_sync_config` in `WebComPyBuildConfig`
- **THEN** lock file sync commands SHALL use auto-discovery (walk up from `app_package_path` to find `pyproject.toml`)
- **AND** `--sync` SHALL compare `[project.dependencies]` by default

### ADDED: webcompy init template shall use webcompy_cli.config import

The `webcompy init` template SHALL generate `webcompy_config.py` with the import `from webcompy_cli.config import WebComPyBuildConfig, WebComPyServerConfig` as the canonical import path.

#### Scenario: Generated template uses canonical import
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** the generated `webcompy_config.py` SHALL contain `from webcompy_cli.config import WebComPyBuildConfig`
- **AND** the generated config SHALL work identically with either import path (legacy or canonical)