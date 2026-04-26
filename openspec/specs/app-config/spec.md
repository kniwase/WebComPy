# Application Configuration

## Purpose

Application configuration provides type-safe, validated settings for WebComPy applications. `AppConfig` is the sole developer-facing configuration class, containing settings shared between browser and server environments. `ServerConfig` and `GenerateConfig` are internal dataclasses used by CLI functions, not exported in the public API.

## Requirements

### Requirement: Application configuration shall use type-safe dataclasses
The framework SHALL provide `AppConfig`, `ServerConfig`, and `GenerateConfig` dataclasses with validated fields and sensible defaults. `AppConfig` SHALL contain settings shared between browser and server environments (including `app_package` for server-side use). `ServerConfig` and `GenerateConfig` are internal types used by CLI functions, not part of the public API surface. `AppConfig` is the sole developer-facing configuration class.

#### Scenario: Creating a minimal application configuration
- **WHEN** a developer creates `AppConfig()` without explicit config
- **THEN** default `AppConfig` values SHALL be used (`base_url="/"`, `dependencies=[]`, `assets=None`, `app_package="."`, `profile=False`, `hydrate=True`, `version=None`)
- **AND** the app SHALL function correctly with these defaults

#### Scenario: Configuring profiling and hydration
- **WHEN** a developer creates `AppConfig(profile=True, hydrate=False)`
- **THEN** `profile` SHALL be stored as `True`
- **AND** `hydrate` SHALL be stored as `False`
- **AND** the generated HTML SHALL include profiling bootstrap code when `profile=True`
- **AND** `WebComPyApp.__init__()` SHALL also accept a `profile` parameter directly; when `profile` is not explicitly `True`, `config.profile` SHALL be read to determine the effective value

#### Scenario: Hydrate parameter on WebComPyApp overrides AppConfig
- **WHEN** a developer creates `WebComPyApp(..., hydrate=False, config=AppConfig(hydrate=True))`
- **THEN** the explicit `hydrate=False` parameter SHALL take precedence over `config.hydrate`

#### Scenario: Hydrate defaults from AppConfig
- **WHEN** a developer creates `WebComPyApp(..., config=AppConfig(hydrate=True))` without an explicit `hydrate` parameter
- **THEN** `config.hydrate` SHALL be used as the effective value

#### Scenario: Configuring base URL and dependencies
- **WHEN** a developer creates `AppConfig(base_url="/myapp/", dependencies=["pandas"])`
- **THEN** `base_url` SHALL be normalized to `"/myapp/"` (trailing slash)
- **AND** `dependencies` SHALL be stored as a copy of the provided list

#### Scenario: Configuring app version
- **WHEN** a developer creates `AppConfig(version="1.0.0")`
- **THEN** `version` SHALL be stored as `"1.0.0"`
- **AND** the wheel METADATA SHALL include `Version: 0+sha.{hash8}` (content-derived hash overrides the configured version for PEP 427 compliance)
- **AND** the wheel URL SHALL change when application code changes (content-hash cache busting)

#### Scenario: Passing configuration to WebComPyApp
- **WHEN** a developer creates `WebComPyApp(root_component=Root, config=AppConfig(base_url="/app/"))`
- **THEN** the app SHALL use the provided configuration
- **AND** the router SHALL use `base_url="/app/"` for URL handling

### Requirement: AppConfig base_url shall normalize input
`AppConfig.base_url` SHALL accept strings with or without leading/trailing slashes and normalize them to the form `/path/` (or `/` for root).

#### Scenario: Normalizing base URLs
- **WHEN** a developer provides `base_url="myapp"`
- **THEN** it SHALL be normalized to `"/myapp/"`
- **WHEN** a developer provides `base_url="/myapp"`
- **THEN** it SHALL be normalized to `"/myapp/"`
- **WHEN** a developer provides `base_url=""`
- **THEN** it SHALL be normalized to `"/"`

### Requirement: AppConfig assets shall map keys to file paths
`AppConfig.assets` SHALL accept an optional mapping of string keys to file paths relative to the app package directory. These assets SHALL be included in the bundled wheel and accessible at runtime via `load_asset`.

#### Scenario: Configuring assets
- **WHEN** a developer provides `assets={"logo": "images/logo.png"}`
- **THEN** the asset SHALL be included in the bundled wheel
- **AND** `load_asset("logo")` SHALL return the file content as `bytes`

#### Scenario: Omitting assets
- **WHEN** a developer does not provide `assets`
- **THEN** `assets` SHALL default to `None`
- **AND** no assets SHALL be included in the bundled wheel

### Requirement: AppConfig dependencies shall default to None and support auto-population from pyproject.toml
`AppConfig.dependencies` SHALL accept `None` as a default value (instead of `[]`). When `dependencies` is `None`, the CLI SHALL auto-populate it from `pyproject.toml` using the group specified by `dependencies_from`. When `dependencies` is explicitly set to a list, it SHALL be used as-is without reading `pyproject.toml`. This eliminates the need for developers to manually duplicate dependency lists in both `AppConfig` and `pyproject.toml`.

#### Scenario: Auto-populating dependencies from pyproject.toml optional-dependencies
- **WHEN** a developer creates `AppConfig(dependencies=None, dependencies_from="browser")`
- **AND** `pyproject.toml` contains `[project.optional-dependencies] browser = ["numpy", "matplotlib"]`
- **THEN** the CLI SHALL set `app.config.dependencies` to `["numpy", "matplotlib"]`
- **AND** the lock file SHALL be generated as if the developer had written `AppConfig(dependencies=["numpy", "matplotlib"])`

#### Scenario: Auto-populating dependencies from pyproject.toml project.dependencies
- **WHEN** a developer creates `AppConfig(dependencies=None, dependencies_from=None)`
- **AND** `pyproject.toml` contains `[project] dependencies = ["flask", "click"]`
- **THEN** the CLI SHALL set `app.config.dependencies` to `["flask", "click"]`

#### Scenario: Explicit dependencies take precedence
- **WHEN** a developer creates `AppConfig(dependencies=["numpy"])`
- **THEN** the CLI SHALL use `["numpy"]` as-is
- **AND** no `pyproject.toml` dependency reading SHALL occur

#### Scenario: Empty explicit dependencies list
- **WHEN** a developer creates `AppConfig(dependencies=[])`
- **THEN** the CLI SHALL use `[]` (no dependencies)
- **AND** no `pyproject.toml` dependency reading SHALL occur

#### Scenario: Pyproject.toml not found with None dependencies
- **WHEN** a developer creates `AppConfig(dependencies=None)`
- **AND** no `pyproject.toml` is found above `app_package_path`
- **THEN** an error SHALL be reported instructing the developer to either set `AppConfig.dependencies` explicitly or ensure `pyproject.toml` exists

#### Scenario: Optional-dependencies group not found
- **WHEN** a developer creates `AppConfig(dependencies=None, dependencies_from="browser")`
- **AND** `pyproject.toml` exists but `[project.optional-dependencies]` has no `"browser"` key
- **THEN** an error SHALL be reported indicating that the `"browser"` group was not found in `pyproject.toml`

#### Scenario: Dependency version specifiers are stripped
- **WHEN** `pyproject.toml` contains `dependencies = ["flask==3.1.0", "click>=8.0"]`
- **AND** a developer creates `AppConfig(dependencies=None, dependencies_from=None)`
- **THEN** the CLI SHALL extract package names as `["flask", "click"]`
- **AND** version specifiers SHALL be stripped (version pinning is handled by `webcompy-lock.json`)

### Requirement: AppConfig dependencies_from shall default to None and read project.dependencies
`AppConfig.dependencies_from` SHALL default to `None`. When `None`, `[project.dependencies]` from `pyproject.toml` is used. When set to a string value (e.g., `"browser"`), `[project.optional-dependencies.{value}]` is used.

#### Scenario: Default dependencies_from reads project.dependencies
- **WHEN** `AppConfig(dependencies=None)` is created without `dependencies_from`
- **THEN** `[project.dependencies]` from `pyproject.toml` SHALL be read

#### Scenario: dependencies_from mismatch warning
- **WHEN** `AppConfig.dependencies_from="browser"` differs from `LockfileSyncConfig.sync_group`
- **THEN** a warning SHALL be emitted indicating the mismatch and potential inconsistency

### Requirement: Only WASM packages shall be loaded from the Pyodide CDN; pure-Python CDN packages are not bundled
Pure-Python packages available in the Pyodide CDN SHALL NOT be bundled into the app wheel. They are already available from the Pyodide CDN and will be loaded by the browser from there. Only WASM packages (which cannot be bundled as pure Python) SHALL appear in `py-config.packages` for Pyodide CDN loading. There is no configuration option to change this behavior.

#### Scenario: Pure-Python package available in Pyodide CDN
- **WHEN** a dependency (e.g., `httpx`) is a pure-Python package available in the Pyodide CDN
- **THEN** it SHALL NOT be bundled into the app wheel
- **AND** it SHALL NOT appear in `py-config.packages`

#### Scenario: WASM-only dependency
- **WHEN** a dependency (e.g., `numpy`) is a WASM package in Pyodide
- **THEN** the dependency SHALL be loaded from the Pyodide CDN because it cannot be bundled as pure Python
- **AND** it SHALL appear in `py-config.packages` as a plain package name

### Requirement: ServerConfig and GenerateConfig shall be internal
`ServerConfig` and `GenerateConfig` SHALL be internal dataclasses used by CLI functions. They SHALL NOT be exported in `webcompy.__all__` or `webcompy.app.__all__`. Developers define them in `webcompy_server_config.py`, which the CLI reads from the app package or the project root.

#### Scenario: ServerConfig defaults
- **WHEN** no `webcompy_server_config.py` exists (in the app package or at the project root) or it does not define `server_config`
- **THEN** `ServerConfig()` defaults SHALL be used (`port=8080`, `dev=False`, `static_files_dir="static"`)

#### Scenario: GenerateConfig defaults
- **WHEN** no `webcompy_server_config.py` exists (in the app package or at the project root) or it does not define `generate_config`
- **THEN** `GenerateConfig()` defaults SHALL be used (`dist="dist"`, `cname=""`, `static_files_dir="static"`)