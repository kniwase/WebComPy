# Application Configuration

## Purpose

Application configuration provides type-safe, validated settings for WebComPy applications. `AppConfig` is the sole developer-facing configuration class, containing settings shared between browser and server environments. `ServerConfig` and `GenerateConfig` are internal dataclasses used by CLI functions, not exported in the public API.

## Requirements

### Requirement: Application configuration shall use type-safe dataclasses
The framework SHALL provide `AppConfig`, `ServerConfig`, and `GenerateConfig` dataclasses with validated fields and sensible defaults. `AppConfig` SHALL contain settings shared between browser and server environments (including `app_package` for server-side use). `ServerConfig` and `GenerateConfig` are internal types used by CLI functions, not part of the public API surface. `AppConfig` is the sole developer-facing configuration class.

#### Scenario: Creating a minimal application configuration
- **WHEN** a developer creates `WebComPyApp(root_component=Root)` without explicit config
- **THEN** default `AppConfig` values SHALL be used (`base_url="/"`, `dependencies=[]`, `assets=None`, `app_package="."`, `profile=False`, `hydrate=True`, `version=None`)
- **AND** the app SHALL function correctly with these defaults

#### Scenario: Configuring profiling and hydration
- **WHEN** a developer creates `AppConfig(profile=True, hydrate=False)`
- **THEN** `profile` SHALL be stored as `True`
- **AND** `hydrate` SHALL be stored as `False`
- **AND** the generated HTML SHALL include profiling bootstrap code when `profile=True`

#### Scenario: Configuring app version
- **WHEN** a developer creates `AppConfig(version="1.0.0")`
- **THEN** `version` SHALL be stored as `"1.0.0"`
- **AND** the wheel METADATA SHALL include `Version: 1.0.0`
- **AND** the wheel URL SHALL remain stable without a version suffix

#### Scenario: Configuring base URL and dependencies
- **WHEN** a developer creates `AppConfig(base_url="/myapp/", dependencies=["pandas"])`
- **THEN** `base_url` SHALL be normalized to `"/myapp/"` (trailing slash)
- **AND** `dependencies` SHALL be stored as a copy of the provided list

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

### Requirement: ServerConfig and GenerateConfig shall be internal
`ServerConfig` and `GenerateConfig` SHALL be internal dataclasses used by CLI functions. They SHALL NOT be exported in `webcompy.__all__` or `webcompy.app.__all__`. Developers define them in `webcompy_server_config.py`, which the CLI reads from the app package or the project root.

#### Scenario: ServerConfig defaults
- **WHEN** no `webcompy_server_config.py` exists (in the app package or at the project root) or it does not define `server_config`
- **THEN** `ServerConfig()` defaults SHALL be used (`port=8080`, `dev=False`, `static_files_dir="static"`)

#### Scenario: GenerateConfig defaults
- **WHEN** no `webcompy_server_config.py` exists (in the app package or at the project root) or it does not define `generate_config`
- **THEN** `GenerateConfig()` defaults SHALL be used (`dist="dist"`, `cname=""`, `static_files_dir="static"`)