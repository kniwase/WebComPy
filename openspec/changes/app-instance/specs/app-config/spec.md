## ADDED Requirements

### Requirement: Application configuration shall use type-safe dataclasses
The framework SHALL provide `AppConfig`, `ServerConfig`, and `GenerateConfig` dataclasses with validated fields and sensible defaults. `AppConfig` SHALL contain settings shared between browser and server environments (including `app_package` for server-side use). `ServerConfig` and `GenerateConfig` are internal types used by CLI functions, not passed directly by developers through `WebComPyApp`.

#### Scenario: Creating a minimal application configuration
- **WHEN** a developer creates `WebComPyApp(root_component=Root)` without explicit config
- **THEN** default `AppConfig` values SHALL be used (`base_url="/"`, `dependencies=[]`, `assets=None`)
- **AND** the app SHALL function correctly with these defaults

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