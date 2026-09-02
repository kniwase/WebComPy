# Spec delta: app-config

## MODIFIED Requirements

### Requirement: WebComPyBuildConfig shall contain all build-time settings
`WebComPyBuildConfig` SHALL be a dataclass containing all settings needed for SSR/SSG builds, wheel packaging, and dependency resolution. It SHALL accept the app's Python module object (`app_module`) as its first required positional argument and `app_var: str = "app"` as an optional keyword argument for the instance variable name. In `__post_init__`, it SHALL compute `app = getattr(app_module, app_var)` and `app_package_path = Path(app_module.__file__).parent`. It SHALL be importable from `webcompy_cli.config` (with legacy shim at `webcompy.cli.config`). `WebComPyBuildConfig` SHALL include fields from the former `AppConfig` (server-only fields), `GenerateConfig`, and `ServerConfig` (as a nested `server` field).

#### Scenario: Creating a minimal WebComPyBuildConfig
- **WHEN** a developer creates `WebComPyBuildConfig(app_module)` where `app_module` is the `my_app.app` module object
- **AND** `app_module.__file__` is `/path/to/my_app/app.py`
- **THEN** `config.app_package_path` SHALL be `/path/to/my_app/` (computed from `Path(app_module.__file__).parent`)
- **AND** `config.app` SHALL be the `WebComPyApp` instance from `getattr(app_module, "app")` (default `app_var`)
- **AND** default values SHALL be `dependencies=None`, `dependencies_from=None`, `assets=None`, `version=None`, `serve_all_deps=True`, `wasm_serving=None`, `runtime_serving=None`, `standalone=False`, `wheel_mode="bundled"`, `dist="dist"`, `static_files_dir="static"`, `lockfile_sync_config=None`
- **AND** `server` SHALL default to `WebComPyServerConfig()`

#### Scenario: Creating a WebComPyBuildConfig with custom app_var
- **WHEN** a developer creates `WebComPyBuildConfig(app_module, app_var="my_app_instance")`
- **THEN** `config.app` SHALL be `getattr(app_module, "my_app_instance")`

#### Scenario: app_package_path derivation from app_module.__file__
- **WHEN** `import my_app.app as app_module` and `app_module.__file__` is `/home/project/my_app/app.py`
- **THEN** `config.app_package_path` SHALL be `/home/project/my_app/`
- **AND** `config.app_package_path.name` SHALL be `"my_app"`

#### Scenario: Creating a WebComPyBuildConfig with nested server config
- **WHEN** a developer creates `WebComPyBuildConfig(app_module, server=WebComPyServerConfig(port=3000, dev=True))`
- **THEN** `server.port` SHALL be `3000`
- **AND** `server.dev` SHALL be `True`
