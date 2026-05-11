## MODIFIED Requirements

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

### Requirement: AppConfig base_url shall normalize input
`WebComPyAppConfig.base_url` SHALL accept strings with or without leading/trailing slashes and normalize them to the form `/path/` (or `/` for root).

#### Scenario: Normalizing base URLs
- **WHEN** a developer provides `base_url="myapp"`
- **THEN** it SHALL be normalized to `"/myapp/"`
- **WHEN** a developer provides `base_url="/myapp"`
- **THEN** it SHALL be normalized to `"/myapp/"`
- **WHEN** a developer provides `base_url=""`
- **THEN** it SHALL be normalized to `"/"`

### Requirement: AppConfig assets shall map keys to file paths
`WebComPyBuildConfig.assets` SHALL accept an optional mapping of string keys to file paths relative to the app package directory. These assets SHALL be included in the bundled wheel and accessible at runtime via `load_asset`.

#### Scenario: Configuring assets
- **WHEN** a developer provides `assets={"logo": "images/logo.png"}`
- **THEN** the asset SHALL be included in the bundled wheel
- **AND** `load_asset("logo")` SHALL return the file content as `bytes`

#### Scenario: Omitting assets
- **WHEN** a developer does not provide `assets`
- **THEN** `assets` SHALL default to `None`
- **AND** no assets SHALL be included in the bundled wheel

### Requirement: AppConfig dependencies shall default to None and support auto-population from pyproject.toml
`WebComPyBuildConfig.dependencies` SHALL accept `None` as a default value (instead of `[]`). When `dependencies` is `None`, the CLI SHALL auto-populate it from `pyproject.toml` using the group specified by `dependencies_from`. When `dependencies` is explicitly set to a list, it SHALL be used as-is without reading `pyproject.toml`.

#### Scenario: Auto-populating dependencies from pyproject.toml optional-dependencies
- **WHEN** a developer creates `WebComPyBuildConfig(app, dependencies=None, dependencies_from="browser")`
- **AND** `pyproject.toml` contains `[project.optional-dependencies] browser = ["numpy", "matplotlib"]`
- **THEN** the CLI SHALL set `config.dependencies` to `["numpy", "matplotlib"]`

#### Scenario: Explicit dependencies take precedence
- **WHEN** a developer creates `WebComPyBuildConfig(app, dependencies=["numpy"])`
- **THEN** the CLI SHALL use `["numpy"]` as-is
- **AND** no `pyproject.toml` dependency reading SHALL occur

### Requirement: AppConfig dependencies_from shall default to None and read project.dependencies
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

### Requirement: AppConfig shall include a wasm_serving field for controlling WASM package delivery
`WebComPyBuildConfig` SHALL include a `wasm_serving: Literal["cdn", "local"] | None = None` field. When `None` or `"cdn"`, WASM packages are loaded from the Pyodide CDN. When `"local"`, WASM package wheel files are downloaded at build time and served from the same origin.

#### Scenario: Default CDN mode
- **WHEN** a developer creates `WebComPyBuildConfig(app)` without `wasm_serving`
- **THEN** WASM packages SHALL be loaded from the Pyodide CDN

#### Scenario: Local WASM serving mode
- **WHEN** a developer creates `WebComPyBuildConfig(app, wasm_serving="local")`
- **THEN** WASM packages SHALL be downloaded and served locally

### Requirement: AppConfig shall include a runtime_serving field for controlling PyScript/Pyodide runtime delivery
`WebComPyBuildConfig` SHALL include a `runtime_serving: Literal["cdn", "local"] | None = None` field. When `None` (default), the effective value is `"cdn"`. When `"local"`, all runtime assets are downloaded at build time and served from the same origin.

#### Scenario: Default CDN mode
- **WHEN** a developer creates `WebComPyBuildConfig(app)` without `runtime_serving`
- **THEN** PyScript and Pyodide runtime assets SHALL be loaded from CDN URLs

#### Scenario: Local runtime serving mode
- **WHEN** a developer creates `WebComPyBuildConfig(app, runtime_serving="local")`
- **THEN** all runtime assets SHALL be downloaded and served locally

### Requirement: AppConfig shall include a standalone flag for complete offline capability
`WebComPyBuildConfig` SHALL include a `standalone: bool = False` field. When `True`, all local-serving modes are enabled simultaneously. Individual config options explicitly set by the developer SHALL take precedence over `standalone` defaults.

#### Scenario: Enabling standalone mode with defaults
- **WHEN** a developer creates `WebComPyBuildConfig(app, standalone=True)` without overriding individual settings
- **THEN** `serve_all_deps` SHALL be `True`
- **AND** `wasm_serving` SHALL be `"local"`
- **AND** `runtime_serving` SHALL be `"local"`

#### Scenario: Individual overrides take precedence
- **WHEN** a developer creates `WebComPyBuildConfig(app, standalone=True, wasm_serving="cdn")`
- **THEN** the explicit `wasm_serving="cdn"` SHALL take precedence

### Requirement: AppConfig shall include a wheel_mode field for controlling wheel bundling strategy
`WebComPyBuildConfig` SHALL include a `wheel_mode: Literal["bundled", "split"] = "bundled"` field.

#### Scenario: Default bundled mode
- **WHEN** a developer creates `WebComPyBuildConfig(app)` without `wheel_mode`
- **THEN** a single bundled wheel SHALL be produced

#### Scenario: Split mode
- **WHEN** a developer creates `WebComPyBuildConfig(app, wheel_mode="split")`
- **THEN** two wheels SHALL be produced: framework wheel and app wheel

### Requirement: AppConfig shall include a plugins field for declarative plugin discovery
`WebComPyAppConfig` SHALL include a `plugins: list[str]` field that defaults to an empty list. Each string SHALL be an absolute module path with a colon-separated class name. Plugins are discovered and initialized by `PluginManager` during `WebComPyApp.__init__()`.

#### Scenario: Configuring plugins
- **WHEN** a developer creates `WebComPyAppConfig(plugins=["myapp.plugins:ErudaPlugin"])`
- **THEN** the plugin SHALL be discovered and initialized

### Requirement: AppConfig shall include a scripts field for declarative conditional script loading
`WebComPyAppConfig` SHALL include a `scripts: list[PluginScript]` field that defaults to an empty list. The `PluginScript` dataclass SHALL be defined in `webcompy.app._config` and exported in the public API.

#### Scenario: Default scripts value
- **WHEN** a developer creates `WebComPyAppConfig()` without `scripts`
- **THEN** `scripts` SHALL default to an empty list

### Requirement: CLI flags shall override config file values
CLI flags SHALL override values from `webcompy_config.py` and the defaults. The `--config` flag SHALL accept a path to a `webcompy_config.py` file. When not provided, the CLI SHALL look for `webcompy_config.py` in the current working directory.

#### Scenario: Overriding port with --port
- **WHEN** `webcompy_config.py` sets `config = WebComPyBuildConfig(app, server=WebComPyServerConfig(port=8080))`
- **AND** a developer runs `python -m webcompy start --port 3000`
- **THEN** the server SHALL start on port 3000

#### Scenario: Overriding with --no-serve-all-deps
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **THEN** `serve_all_deps` SHALL be `False` for the session

## REMOVED Requirements

### Requirement: Application configuration shall use type-safe dataclasses (AppConfig)
**Reason**: `AppConfig` is replaced by `WebComPyAppConfig` (browser-relevant) and `WebComPyBuildConfig` (server-only). The former mixed responsibilities are now separated.
**Migration**: Use `WebComPyAppConfig` for browser-relevant settings (imported from `webcompy.app`) and `WebComPyBuildConfig` for build settings (imported from `webcompy.cli.config`). Move server-only fields from `AppConfig` to `WebComPyBuildConfig`.

### Requirement: AppConfig shall include a serve_all_deps field for controlling dependency delivery
**Reason**: `serve_all_deps` moves from `AppConfig` to `WebComPyBuildConfig`.
**Migration**: Use `WebComPyBuildConfig(app, serve_all_deps=True)`.

### Requirement: Only WASM packages shall be loaded from the Pyodide CDN by name; pure-Python CDN package handling depends on serve_all_deps
**Reason**: This requirement is updated in the `cli` spec to reference `WebComPyBuildConfig.serve_all_deps` instead of `AppConfig.serve_all_deps`.
**Migration**: See the updated `cli` spec.

### Requirement: CLI flags shall override serve_all_deps
**Reason**: Moved to `cli` spec as it references CLI flags operating on `WebComPyBuildConfig`.
**Migration**: See the updated `cli` spec.

### Requirement: static_files_dir resolution shall be handled by call sites
**Reason**: `static_files_dir` is now a field of `WebComPyBuildConfig` (absorbed from `GenerateConfig`). Resolution is unchanged but the source config class changes.
**Migration**: Use `WebComPyBuildConfig(app, static_files_dir="static")`. Path resolution by call sites is unchanged.

### Requirement: ServerConfig and GenerateConfig shall be internal
**Reason**: `GenerateConfig` is absorbed into `WebComPyBuildConfig`. `ServerConfig` becomes `WebComPyServerConfig` (a member of `WebComPyBuildConfig`).
**Migration**: Use `WebComPyBuildConfig` for all build/SSG settings. Use `WebComPyServerConfig` for ASGI server settings (nested as `WebComPyBuildConfig.server`).

### Requirement: CLI flags shall override wasm_serving
**Reason**: Moved to `cli` spec as it references CLI flags operating on `WebComPyBuildConfig`.
**Migration**: See the updated `cli` spec.

### Requirement: CLI flags shall override runtime_serving
**Reason**: Moved to `cli` spec as it references CLI flags operating on `WebComPyBuildConfig`.
**Migration**: See the updated `cli` spec.

### Requirement: Hydrate parameter on WebComPyApp overrides AppConfig
**Reason**: The `hydrate` parameter on `WebComPyApp.__init__` is removed. Hydration is now set exclusively via `WebComPyAppConfig.hydrate`.
**Migration**: Use `WebComPyAppConfig(hydrate=False)` instead of `WebComPyApp(..., hydrate=False)`.

### Requirement: Switching standalone mode shall take effect on a fresh configuration
**Reason**: The standalone switching logic moves from `AppConfig` to `WebComPyBuildConfig`. The behavior is unchanged but operates on the new config class.
**Migration**: Use `WebComPyBuildConfig(app, standalone=True)` instead of `AppConfig(standalone=True)`.