# Application Configuration

## Purpose

Application configuration provides type-safe, validated settings for WebComPy applications. `AppConfig` is the sole developer-facing configuration class, containing settings shared between browser and server environments. `ServerConfig` and `GenerateConfig` are internal dataclasses used by CLI functions, not exported in the public API.

## Requirements

### Requirement: Application configuration shall use type-safe dataclasses
The framework SHALL provide `AppConfig`, `ServerConfig`, and `GenerateConfig` dataclasses with validated fields and sensible defaults. `AppConfig` SHALL contain settings shared between browser and server environments (including `app_package` for server-side use). `ServerConfig` and `GenerateConfig` are internal types used by CLI functions, not part of the public API surface. `AppConfig` is the sole developer-facing configuration class.

#### Scenario: Creating a minimal application configuration
- **WHEN** a developer creates `AppConfig()` without explicit config
- **THEN** default `AppConfig` values SHALL be used (`base_url="/"`, `dependencies=None`, `assets=None`, `app_package="."`, `profile=False`, `hydrate=True`, `version=None`, `serve_all_deps=True`)
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

### Requirement: AppConfig shall include a serve_all_deps field for controlling dependency delivery
`AppConfig` SHALL include a `serve_all_deps: bool = True` field. When `True` (default), all pure-Python packages that the WebComPy server can provide are served from the same origin — either bundled from local installation or downloaded from the Pyodide CDN and then bundled. When `False`, pure-Python packages available in the Pyodide CDN are loaded from the CDN by name via `py-config.packages`, and only packages not available from the CDN are bundled.

#### Scenario: Default serve_all_deps behavior
- **WHEN** a developer creates `AppConfig()` without `serve_all_deps`
- **THEN** `serve_all_deps` SHALL be `True`
- **AND** all pure-Python packages SHALL be bundled into the app wheel
- **AND** only WASM package names SHALL appear in `py-config.packages`

#### Scenario: Explicit serve_all_deps=True
- **WHEN** a developer creates `AppConfig(serve_all_deps=True)`
- **THEN** pure-Python packages in the Pyodide CDN SHALL be downloaded at build time and bundled into the app wheel
- **AND** pure-Python packages NOT in the Pyodide CDN SHALL be bundled from local installation
- **AND** only WASM package names SHALL appear in `py-config.packages`

#### Scenario: Explicit serve_all_deps=False
- **WHEN** a developer creates `AppConfig(serve_all_deps=False)`
- **THEN** pure-Python packages in the Pyodide CDN SHALL NOT be bundled
- **AND** their package names SHALL appear in `py-config.packages` for CDN loading
- **AND** pure-Python packages NOT in the Pyodide CDN SHALL be bundled from local installation
- **AND** WASM package names SHALL appear in `py-config.packages`

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

### Requirement: Pure-Python packages in the Pyodide CDN shall be bundled when serve_all_deps is True
When `serve_all_deps=True`, pure-Python packages available in the Pyodide CDN SHALL be bundled into the app wheel. This replaces the previous behavior where they were neither bundled nor loaded from the CDN, making them unavailable in the browser.

#### Scenario: Pure-Python CDN package with serve_all_deps=True
- **WHEN** `AppConfig(dependencies=["httpx"], serve_all_deps=True)` and `httpx` is a pure-Python package in the Pyodide CDN
- **THEN** `httpx` SHALL be downloaded from the Pyodide CDN at build time
- **AND** `httpx` SHALL be bundled into the app wheel
- **AND** `httpx` SHALL NOT appear in `py-config.packages`

#### Scenario: Pure-Python CDN package with serve_all_deps=False
- **WHEN** `AppConfig(dependencies=["httpx"], serve_all_deps=False)` and `httpx` is a pure-Python package in the Pyodide CDN
- **THEN** `httpx` SHALL NOT be bundled into the app wheel
- **AND** `httpx` SHALL appear in `py-config.packages` as a plain package name

### Requirement: Only WASM packages shall be loaded from the Pyodide CDN by name; pure-Python CDN package handling depends on serve_all_deps
Only WASM packages SHALL always be loaded from the Pyodide CDN by name via `py-config.packages`. Pure-Python packages available in the Pyodide CDN SHALL be either bundled (when `serve_all_deps=True`) or loaded from the CDN by name (when `serve_all_deps=False`).

#### Scenario: WASM package (regardless of serve_all_deps)
- **WHEN** a dependency is a WASM package in the Pyodide CDN
- **THEN** it SHALL always be loaded from the CDN by name via `py-config.packages`
- **AND** it SHALL NOT be bundled

### Requirement: CLI flags shall override serve_all_deps
The `start` and `generate` CLI subcommands SHALL accept `--serve-all-deps` and `--no-serve-all-deps` flags that override `AppConfig.serve_all_deps`.

#### Scenario: Overriding with --no-serve-all-deps
- **WHEN** a developer runs `python -m webcompy start --dev --no-serve-all-deps`
- **THEN** `serve_all_deps` SHALL be `False` for the session
- **AND** CDN-available pure-Python packages SHALL be loaded from CDN

#### Scenario: Overriding with --serve-all-deps
- **WHEN** a developer runs `python -m webcompy generate --serve-all-deps`
- **THEN** `serve_all_deps` SHALL be `True` for the session
- **AND** CDN-available pure-Python packages SHALL be downloaded and bundled

### Requirement: ServerConfig and GenerateConfig shall be internal
`ServerConfig` and `GenerateConfig` SHALL be internal dataclasses used by CLI functions. They SHALL NOT be exported in `webcompy.__all__` or `webcompy.app.__all__`. Developers define them in `webcompy_server_config.py`, which the CLI reads from the app package or the project root.

#### Scenario: ServerConfig defaults
- **WHEN** no `webcompy_server_config.py` exists (in the app package or at the project root) or it does not define `server_config`
- **THEN** `ServerConfig()` defaults SHALL be used (`port=8080`, `dev=False`, `static_files_dir="static"`)

#### Scenario: GenerateConfig defaults
- **WHEN** no `webcompy_server_config.py` exists (in the app package or at the project root) or it does not define `generate_config`
- **THEN** `GenerateConfig()` defaults SHALL be used (`dist="dist"`, `cname=""`, `static_files_dir="static"`)

### Requirement: AppConfig shall include a wasm_serving field for controlling WASM package delivery
`AppConfig` SHALL include a `wasm_serving: Literal["cdn", "local"] | None = None` field. When `None` or `"cdn"`, WASM packages are loaded from the Pyodide CDN by package name. When `"local"`, WASM package wheel files are downloaded at build time and served from the same origin. The `None` sentinel enables `standalone` mode (in `feat-standalone`) to distinguish between "unset" (overridden to `"local"`) and "explicitly set to `"cdn"`" (preserved).

#### Scenario: Default CDN mode
- **WHEN** a developer creates `AppConfig()` without `wasm_serving`
- **THEN** WASM packages SHALL be loaded from the Pyodide CDN via `py-config.packages` package names

#### Scenario: Local WASM serving mode
- **WHEN** a developer creates `AppConfig(wasm_serving="local")`
- **THEN** WASM package wheel files SHALL be downloaded from the Pyodide CDN at build time
- **AND** they SHALL be served from `/_webcompy-assets/packages/` via local wheel URLs in `py-config.packages`

### Requirement: CLI flags shall override wasm_serving
The `start` and `generate` CLI subcommands SHALL accept `--wasm-serving <mode>` (where `<mode>` is `cdn` or `local`) that overrides `AppConfig.wasm_serving`. This follows the value-argument pattern rather than the boolean toggle pattern, because `wasm_serving` has more than two meaningful values in future extensions.

#### Scenario: Overriding with --wasm-serving local
- **WHEN** a developer runs `python -m webcompy start --dev --wasm-serving local`
- **THEN** `wasm_serving` SHALL be `"local"` for the session
- **AND** WASM packages SHALL be downloaded and served locally

#### Scenario: Overriding with --wasm-serving cdn
- **WHEN** a developer runs `python -m webcompy generate --wasm-serving cdn`
- **THEN** `wasm_serving` SHALL be `"cdn"` for the session
- **AND** WASM packages SHALL be loaded from the Pyodide CDN by name

#### Scenario: Default when no flag is provided
- **WHEN** a developer runs `python -m webcompy start --dev` without `--wasm-serving`
- **THEN** `wasm_serving` SHALL use the value from `AppConfig.wasm_serving` (default `"cdn"`)

### Requirement: AppConfig shall include a wasm_serving field for controlling WASM package delivery
`AppConfig` SHALL include a `wasm_serving: Literal["cdn", "local"] | None = None` field. When `None` or `"cdn"`, WASM packages are loaded from the Pyodide CDN by package name. When `"local"`, WASM package wheel files are downloaded at build time and served from the same origin. The `None` sentinel enables `standalone` mode (in `feat-standalone`) to distinguish between "unset" (overridden to `"local"`) and "explicitly set to `"cdn"`" (preserved).

#### Scenario: Default CDN mode
- **WHEN** a developer creates `AppConfig()` without `wasm_serving`
- **THEN** WASM packages SHALL be loaded from the Pyodide CDN via `py-config.packages` package names

#### Scenario: Local WASM serving mode
- **WHEN** a developer creates `AppConfig(wasm_serving="local")`
- **THEN** WASM package wheel files SHALL be downloaded from the Pyodide CDN at build time
- **AND** they SHALL be served from `/_webcompy-assets/packages/` via local wheel URLs in `py-config.packages`

### Requirement: CLI flags shall override wasm_serving
The `start` and `generate` CLI subcommands SHALL accept `--wasm-serving <mode>` (where `<mode>` is `cdn` or `local`) that overrides `AppConfig.wasm_serving`. This follows the value-argument pattern rather than the boolean toggle pattern, because `wasm_serving` has more than two meaningful values in future extensions.

#### Scenario: Overriding with --wasm-serving local
- **WHEN** a developer runs `python -m webcompy start --dev --wasm-serving local`
- **THEN** `wasm_serving` SHALL be `"local"` for the session
- **AND** WASM packages SHALL be downloaded and served locally

#### Scenario: Overriding with --wasm-serving cdn
- **WHEN** a developer runs `python -m webcompy generate --wasm-serving cdn`
- **THEN** `wasm_serving` SHALL be `"cdn"` for the session
- **AND** WASM packages SHALL be loaded from the Pyodide CDN by name

#### Scenario: Default when no flag is provided
- **WHEN** a developer runs `python -m webcompy start --dev` without `--wasm-serving`
- **THEN** `wasm_serving` SHALL use the value from `AppConfig.wasm_serving` (default `"cdn"`)