## ADDED Requirements

### Requirement: WebComPyAppConfig shall contain only browser-relevant settings
`WebComPyAppConfig` SHALL be a lightweight dataclass containing only settings relevant to both browser and server environments: `base_url`, `selector`, `profile`, `hydrate`, `scripts`, and `plugins`. It SHALL be importable from `webcompy.app` without importing any server-only modules. `WebComPyAppConfig` SHALL NOT contain any fields related to build configuration, dependency management, or wheel packaging.

#### Scenario: Creating a minimal WebComPyAppConfig
- **WHEN** a developer creates `WebComPyAppConfig()`
- **THEN** default values SHALL be `base_url="/"`, `selector="#webcompy-app"`, `profile=False`, `hydrate=True`, `scripts=[]`, `plugins=[]`

#### Scenario: Creating a WebComPyAppConfig with custom selector
- **WHEN** a developer creates `WebComPyAppConfig(selector="#my-widget")`
- **THEN** `selector` SHALL be `"#my-widget"`

#### Scenario: WebComPyAppConfig is importable in browser environment
- **WHEN** a developer writes `from webcompy.app import WebComPyAppConfig` in PyScript
- **THEN** the import SHALL succeed without importing any CLI or server modules
- **AND** `sys.modules` SHALL NOT contain `webcompy.cli` or `webcompy.cli.config`

#### Scenario: WebComPyAppConfig base_url normalization
- **WHEN** a developer creates `WebComPyAppConfig(base_url="myapp")`
- **THEN** `base_url` SHALL be normalized to `"/myapp/"`
- **WHEN** a developer creates `WebComPyAppConfig(base_url="/myapp")`
- **THEN** `base_url` SHALL be normalized to `"/myapp/"`
- **WHEN** a developer creates `WebComPyAppConfig(base_url="")`
- **THEN** `base_url` SHALL be normalized to `"/"`

### Requirement: WebComPyBuildConfig shall contain all build-time settings
`WebComPyBuildConfig` SHALL be a dataclass containing all settings needed for SSR/SSG builds, wheel packaging, and dependency resolution. It SHALL accept the app's Python module object (`app_module`) as its first required positional argument and `app_var: str = "app"` as an optional keyword argument for the instance variable name. In `__post_init__`, it SHALL compute `app = getattr(app_module, app_var)` and `app_package_path = Path(app_module.__file__).parent`. It SHALL be importable from `webcompy.cli.config` and SHALL NOT be importable from `webcompy.app`. `WebComPyBuildConfig` SHALL include fields from the former `AppConfig` (server-only fields), `GenerateConfig`, and `ServerConfig` (as a nested `server` field).

#### Scenario: Creating a minimal WebComPyBuildConfig
- **WHEN** a developer creates `WebComPyBuildConfig(app_module)` where `app_module` is the `my_app.app` module object
- **AND** `app_module.__file__` is `/path/to/my_app/app.py`
- **THEN** `config.app_package_path` SHALL be `/path/to/my_app/` (computed from `Path(app_module.__file__).parent`)
- **AND** `config.app` SHALL be the `WebComPyApp` instance from `getattr(app_module, "app")` (default `app_var`)
- **AND** default values SHALL be `dependencies=None`, `dependencies_from=None`, `assets=None`, `version=None`, `serve_all_deps=True`, `wasm_serving=None`, `runtime_serving=None`, `standalone=False`, `wheel_mode="bundled"`, `dist="dist"`, `cname=""`, `static_files_dir="static"`, `lockfile_sync_config=None`
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

### Requirement: WebComPyServerConfig shall contain ASGI server settings
`WebComPyServerConfig` SHALL be a lightweight dataclass with `port: int = 8080` and `dev: bool = False`. It SHALL be importable from `webcompy.cli.config` and SHALL NOT be importable from `webcompy.app`. It SHALL be a nested field of `WebComPyBuildConfig` via the `server` attribute.

#### Scenario: Creating a default WebComPyServerConfig
- **WHEN** a developer creates `WebComPyServerConfig()`
- **THEN** `port` SHALL be `8080` and `dev` SHALL be `False`

#### Scenario: WebComPyServerConfig is not importable from webcompy.app
- **WHEN** a developer attempts `from webcompy.app import WebComPyServerConfig`
- **THEN** an `ImportError` SHALL be raised

#### Scenario: WebComPyServerConfig is importable from webcompy.cli.config
- **WHEN** a developer writes `from webcompy.cli.config import WebComPyServerConfig`
- **THEN** the import SHALL succeed

### Requirement: WebComPyApp.run shall use selector from config
`WebComPyApp.run()` SHALL mount the app using `self.config.selector` (defaulting to `"#webcompy-app"`) instead of accepting a `selector` parameter. The `selector` parameter SHALL be removed from `run()`.

#### Scenario: Running app with default selector
- **WHEN** a developer calls `app.run()` with `WebComPyAppConfig(selector="#webcompy-app")`
- **THEN** the app SHALL mount at the `#webcompy-app` element

#### Scenario: Running app with custom selector
- **WHEN** a developer calls `app.run()` with `WebComPyAppConfig(selector="#my-widget")`
- **THEN** the app SHALL mount at the `#my-widget` element

### Requirement: WebComPyApp.__init__ shall not accept profile or hydrate parameters
`WebComPyApp.__init__` SHALL NOT accept `profile` or `hydrate` keyword arguments. These settings SHALL only be set via `WebComPyAppConfig`.

#### Scenario: Creating app with profile via config
- **WHEN** a developer creates `WebComPyApp(root_component=Root, config=WebComPyAppConfig(profile=True))`
- **THEN** the app SHALL have profiling enabled

#### Scenario: Creating app with hydrate via config
- **WHEN** a developer creates `WebComPyApp(root_component=Root, config=WebComPyAppConfig(hydrate=False))`
- **THEN** the app SHALL have hydration disabled

#### Scenario: Passing profile or hydrate to __init__ raises TypeError
- **WHEN** a developer creates `WebComPyApp(root_component=Root, config=WebComPyAppConfig(), profile=True)`
- **THEN** a `TypeError` SHALL be raised

### Requirement: SSR/SSG generated HTML shall use selector from config
The SSR and SSG HTML generators SHALL use `app.config.selector` to determine the mount div ID. The generated `<div>` element SHALL use the ID from the selector (without the `#` prefix).

#### Scenario: Generating HTML with default selector
- **WHEN** SSR/SSG generates HTML with `WebComPyAppConfig(selector="#webcompy-app")`
- **THEN** the generated HTML SHALL contain `<div id="webcompy-app">`

#### Scenario: Generating HTML with custom selector
- **WHEN** SSR/SSG generates HTML with `WebComPyAppConfig(selector="#my-widget")`
- **THEN** the generated HTML SHALL contain `<div id="my-widget">`

### Requirement: Library usage shall not require server-only imports
When using WebComPy as a library in PyScript (importing via CDN or direct wheel), a developer SHALL only need to import from `webcompy.app`. No import from `webcompy.cli.config` or `webcompy.cli` SHALL be required for library usage.

#### Scenario: Library usage with minimal imports
- **WHEN** a developer writes in PyScript:
  ```python
  from webcompy.app import WebComPyApp, WebComPyAppConfig
  from my_component import MyComponent

  app = WebComPyApp(root_component=MyComponent, config=WebComPyAppConfig())
  app.run()
  ```
- **THEN** no server-only modules SHALL be imported
- **AND** the app SHALL mount and render correctly