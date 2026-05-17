# Application Configuration

## Purpose

Application configuration provides type-safe, validated settings for WebComPy applications, cleanly separated into browser-relevant settings (`WebComPyAppConfig`) and server-only build settings (`WebComPyBuildConfig`). `WebComPyAppConfig` is importable from `webcompy.app` without importing any server-only modules, enabling library usage in PyScript. `WebComPyBuildConfig` and `WebComPyServerConfig` are importable from `webcompy.cli.config` and are automatically excluded from browser wheels.

## Requirements

### Requirement: Application configuration shall use type-safe dataclasses
The framework SHALL provide `WebComPyAppConfig`, `WebComPyBuildConfig`, and `WebComPyServerConfig` dataclasses with validated fields and sensible defaults. `WebComPyAppConfig` SHALL contain only browser-relevant settings (`base_url`, `selector`, `profile`, `hydrate`, `scripts`, `plugins`) and be importable from `webcompy.app`. `WebComPyBuildConfig` SHALL contain build-time settings and be importable from `webcompy.cli.config`. It SHALL accept the app's Python module object (`app_module`) as its first required positional argument and `app_var: str = "app"` for the instance variable name. `WebComPyServerConfig` SHALL contain ASGI server settings and be importable from `webcompy.cli.config`. `WebComPyServerConfig` is a nested field of `WebComPyBuildConfig` via the `server` attribute. The former `AppConfig` (with mixed browser/server fields), `ServerConfig`, and `GenerateConfig` dataclasses are removed.

#### Scenario: Creating a minimal application configuration
- **WHEN** a developer creates `WebComPyAppConfig()` without explicit config
- **THEN** default `WebComPyAppConfig` values SHALL be used (`base_url="/"`, `selector="#webcompy-app"`, `profile=False`, `hydrate=True`, `scripts=[]`, `plugins=[]`)
- **AND** the app SHALL function correctly with these defaults

#### Scenario: Creating a build configuration
- **WHEN** a developer creates `WebComPyBuildConfig(app_module)` where `app_module` is the app module object (`import my_app.app as app_module`)
- **THEN** `config.app_package_path` SHALL be `/path/to/my_app/` (from `Path(app_module.__file__).parent`)
- **AND** `config.app` SHALL be the `WebComPyApp` instance from `getattr(app_module, "app")`
- **AND** default `WebComPyBuildConfig` values SHALL be used

#### Scenario: Configuring profiling and hydration
- **WHEN** a developer creates `WebComPyAppConfig(profile=True, hydrate=False)`
- **THEN** `profile` SHALL be stored as `True`
- **AND** `hydrate` SHALL be stored as `False`

#### Scenario: Configuring base URL
- **WHEN** a developer creates `WebComPyAppConfig(base_url="/myapp/")`
- **THEN** `base_url` SHALL be normalized to `"/myapp/"`

#### Scenario: Passing configuration to WebComPyApp
- **WHEN** a developer creates `WebComPyApp(root_component=Root, config=WebComPyAppConfig(base_url="/app/"))`
- **THEN** the app SHALL use the provided configuration
- **AND** the router SHALL use `base_url="/app/"` for URL handling

### Requirement: WebComPyAppConfig base_url shall normalize input
`WebComPyAppConfig.base_url` SHALL accept strings with or without leading/trailing slashes and normalize them to the form `/path/` (or `/` for root).

#### Scenario: Normalizing base URLs
- **WHEN** a developer provides `base_url="myapp"`
- **THEN** it SHALL be normalized to `"/myapp/"`
- **WHEN** a developer provides `base_url="/myapp"`
- **THEN** it SHALL be normalized to `"/myapp/"`
- **WHEN** a developer provides `base_url=""`
- **THEN** it SHALL be normalized to `"/"`

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

### Requirement: WebComPyBuildConfig.assets shall map keys to file paths
`WebComPyBuildConfig.assets` SHALL accept an optional mapping of string keys to file paths relative to the app package directory. These assets SHALL be included in the bundled wheel and accessible at runtime via `load_asset`.

#### Scenario: Configuring assets
- **WHEN** a developer provides `assets={"logo": "images/logo.png"}`
- **THEN** the asset SHALL be included in the bundled wheel
- **AND** `load_asset("logo")` SHALL return the file content as `bytes`

#### Scenario: Omitting assets
- **WHEN** a developer does not provide `assets`
- **THEN** `assets` SHALL default to `None`
- **AND** no assets SHALL be included in the bundled wheel

### Requirement: WebComPyBuildConfig.dependencies shall default to None and support auto-population from pyproject.toml
`WebComPyBuildConfig.dependencies` SHALL accept `None` as a default value (instead of `[]`). When `dependencies` is `None`, the CLI SHALL auto-populate it from `pyproject.toml` using the group specified by `dependencies_from`. When `dependencies` is explicitly set to a list, it SHALL be used as-is without reading `pyproject.toml`.

#### Scenario: Auto-populating dependencies from pyproject.toml optional-dependencies
- **WHEN** a developer creates `WebComPyBuildConfig(app, dependencies=None, dependencies_from="browser")`
- **AND** `pyproject.toml` contains `[project.optional-dependencies] browser = ["numpy", "matplotlib"]`
- **THEN** the CLI SHALL set `config.dependencies` to `["numpy", "matplotlib"]`

#### Scenario: Explicit dependencies take precedence
- **WHEN** a developer creates `WebComPyBuildConfig(app, dependencies=["numpy"])`
- **THEN** the CLI SHALL use `["numpy"]` as-is
- **AND** no `pyproject.toml` dependency reading SHALL occur

### Requirement: WebComPyBuildConfig.dependencies_from shall default to None and read project.dependencies
`WebComPyBuildConfig.dependencies_from` SHALL default to `None`. When `None`, `[project.dependencies]` from `pyproject.toml` is used. When set to a string value, `[project.optional-dependencies.{value}]` is used.

#### Scenario: Default dependencies_from reads project.dependencies
- **WHEN** `WebComPyBuildConfig(app, dependencies=None)` is created without `dependencies_from`
- **THEN** `[project.dependencies]` from `pyproject.toml` SHALL be read

### Requirement: Pure-Python packages in the Pyodide CDN shall be bundled when serve_all_deps is True
When `serve_all_deps=True`, pure-Python packages available in the Pyodide CDN SHALL be bundled into the app wheel. This replaces the previous behavior where they were neither bundled nor loaded from the CDN, making them unavailable in the browser.

#### Scenario: Pure-Python CDN package with serve_all_deps=True
- **WHEN** `WebComPyBuildConfig(app, dependencies=["httpx"], serve_all_deps=True)` and `httpx` is a pure-Python package in the Pyodide CDN
- **THEN** `httpx` SHALL be downloaded from the Pyodide CDN at build time
- **AND** `httpx` SHALL be bundled into the app wheel

#### Scenario: Pure-Python CDN package with serve_all_deps=False
- **WHEN** `WebComPyBuildConfig(app, dependencies=["httpx"], serve_all_deps=False)` and `httpx` is a pure-Python package in the Pyodide CDN
- **THEN** `httpx` SHALL NOT be bundled into the app wheel
- **AND** `httpx` SHALL appear in `py-config.packages` as a plain package name

### Requirement: WebComPyBuildConfig shall include a wasm_serving field for controlling WASM package delivery
`WebComPyBuildConfig` SHALL include a `wasm_serving: Literal["cdn", "local"] | None = None` field. When `None` or `"cdn"`, WASM packages are loaded from the Pyodide CDN. When `"local"`, WASM package wheel files are downloaded at build time and served from the same origin.

#### Scenario: Default CDN mode
- **WHEN** a developer creates `WebComPyBuildConfig(app)` without `wasm_serving`
- **THEN** WASM packages SHALL be loaded from the Pyodide CDN

#### Scenario: Local WASM serving mode
- **WHEN** a developer creates `WebComPyBuildConfig(app, wasm_serving="local")`
- **THEN** WASM packages SHALL be downloaded and served locally

### Requirement: WebComPyBuildConfig shall include a runtime_serving field for controlling PyScript/Pyodide runtime delivery
`WebComPyBuildConfig` SHALL include a `runtime_serving: Literal["cdn", "local"] | None = None` field. When `None` (default), the effective value is `"cdn"`. When `"local"`, all runtime assets are downloaded at build time and served from the same origin.

#### Scenario: Default CDN mode
- **WHEN** a developer creates `WebComPyBuildConfig(app)` without `runtime_serving`
- **THEN** PyScript and Pyodide runtime assets SHALL be loaded from CDN URLs

#### Scenario: Local runtime serving mode
- **WHEN** a developer creates `WebComPyBuildConfig(app, runtime_serving="local")`
- **THEN** all runtime assets SHALL be downloaded and served locally

### Requirement: WebComPyBuildConfig shall include a standalone flag for complete offline capability
`WebComPyBuildConfig` SHALL include a `standalone: bool = False` field. When `True`, all local-serving modes are enabled simultaneously. Individual config options explicitly set by the developer SHALL take precedence over `standalone` defaults.

#### Scenario: Enabling standalone mode with defaults
- **WHEN** a developer creates `WebComPyBuildConfig(app, standalone=True)` without overriding individual settings
- **THEN** `serve_all_deps` SHALL be `True`
- **AND** `wasm_serving` SHALL be `"local"`
- **AND** `runtime_serving` SHALL be `"local"`

#### Scenario: Individual overrides take precedence
- **WHEN** a developer creates `WebComPyBuildConfig(app, standalone=True, wasm_serving="cdn")`
- **THEN** the explicit `wasm_serving="cdn"` SHALL take precedence

### Requirement: WebComPyBuildConfig shall include a wheel_mode field for controlling wheel bundling strategy
`WebComPyBuildConfig` SHALL include a `wheel_mode: Literal["bundled", "split"] = "bundled"` field.

#### Scenario: Default bundled mode
- **WHEN** a developer creates `WebComPyBuildConfig(app)` without `wheel_mode`
- **THEN** a single bundled wheel SHALL be produced

#### Scenario: Split mode
- **WHEN** a developer creates `WebComPyBuildConfig(app, wheel_mode="split")`
- **THEN** two wheels SHALL be produced: framework wheel and app wheel

### Requirement: WebComPyAppConfig shall include a plugins field for declarative plugin discovery
`WebComPyAppConfig` SHALL include a `plugins: list[str]` field that defaults to an empty list. Each string SHALL be an absolute module path with a colon-separated class name. Plugins are discovered and initialized by `PluginManager` during `WebComPyApp.__init__()`.

#### Scenario: Configuring plugins
- **WHEN** a developer creates `WebComPyAppConfig(plugins=["myapp.plugins:ErudaPlugin"])`
- **THEN** the plugin SHALL be discovered and initialized

### Requirement: WebComPyAppConfig shall include a scripts field for declarative conditional script loading
`WebComPyAppConfig` SHALL include a `scripts: list[PluginScript]` field that defaults to an empty list. The `PluginScript` dataclass SHALL be defined in `webcompy.app._config` and exported in the public API.

#### Scenario: Default scripts value
- **WHEN** a developer creates `WebComPyAppConfig()` without `scripts`
- **THEN** `scripts` SHALL default to an empty list

### Requirement: CLI flags shall override build config values
CLI flags SHALL override values from `WebComPyBuildConfig`. The following flags SHALL be supported: `--dev`, `--port`, `--dist`, `--config`, `--serve-all-deps`, `--no-serve-all-deps`, `--wasm-serving`, `--runtime-serving`, `--standalone`, `--no-standalone`, `--wheel-mode`.

#### Scenario: Overriding with --no-serve-all-deps
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **THEN** `WebComPyBuildConfig.serve_all_deps` SHALL be `False` for the session

#### Scenario: Overriding with --wasm-serving local
- **WHEN** a developer runs `python -m webcompy start --dev --wasm-serving local`
- **THEN** `WebComPyBuildConfig.wasm_serving` SHALL be `"local"` for the session

#### Scenario: Overriding with --runtime-serving local
- **WHEN** a developer runs `python -m webcompy start --dev --runtime-serving local`
- **THEN** `WebComPyBuildConfig.runtime_serving` SHALL be `"local"` for the session

#### Scenario: Overriding with --standalone
- **WHEN** a developer runs `python -m webcompy generate --standalone`
- **THEN** `WebComPyBuildConfig.standalone` SHALL be `True` for the session

### Requirement: WebComPyBuildConfig shall include a lockfile_sync_config field
`WebComPyBuildConfig` SHALL include a `lockfile_sync_config: LockfileSyncConfig | None = None` field. `LockfileSyncConfig` SHALL be defined in `webcompy.cli.config` with `requirements_path: str | None = None` and `sync_group: str | None = None`.

#### Scenario: Omitting lockfile_sync_config
- **WHEN** a developer creates `WebComPyBuildConfig(app)` without `lockfile_sync_config`
- **THEN** `lockfile_sync_config` SHALL default to `None`
- **AND** lock file sync commands SHALL use auto-discovery

### Requirement: App provides ports during bootstrap
`WebComPyApp` SHALL instantiate and provide browser or server port implementations into `app.di_scope` during `__init__`, based on the current environment.

#### Scenario: Browser ports provided
- **WHEN** `WebComPyApp.__init__` runs in PyScript environment
- **THEN** `BrowserDOMPort()`, `BrowserFFIPort()`, `BrowserFetchPort()`, `BrowserHistoryPort()` SHALL be provided into `app.di_scope`
- **AND** all ports SHALL be available via `inject()` during subsequent rendering

#### Scenario: Server ports provided
- **WHEN** `WebComPyApp.__init__` runs in server environment
- **THEN** `ServerDOMPort()`, `ServerFFIPort()`, `ServerFetchPort()`, `ServerHistoryPort()` SHALL be provided into `app.di_scope`

#### Scenario: Ports provided before root component construction
- **WHEN** `WebComPyApp.__init__` bootstraps the application
- **THEN** ports SHALL be provided before `AppDocumentRoot` is constructed
- **AND** the root component SHALL have access to all ports during its first render