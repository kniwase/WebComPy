# Application Configuration Changes

## ADDED Requirements

### Requirement: AppConfig shall include a scripts field for declarative conditional script loading

`AppConfig` SHALL include a `scripts: list[PluginScript]` field that defaults to an empty list. This field allows developers to declaratively define scripts that may be conditionally loaded at runtime in the browser. The `PluginScript` dataclass SHALL be defined in the same module (`webcompy/app/_config.py`) and exported in the public API.

#### Scenario: Default scripts value
- **WHEN** a developer creates `AppConfig()` without `scripts`
- **THEN** `scripts` SHALL default to an empty list `[]`
- **AND** no additional `<script>` tags SHALL appear in the generated HTML

#### Scenario: Configuring conditional scripts
- **WHEN** a developer creates `AppConfig(scripts=[PluginScript(attrs={"src": "https://example.com/debug.js"}, condition="location.search.includes('debug')")])`
- **THEN** the configured scripts SHALL be passed to `generate_html()`
- **AND** the generated HTML SHALL contain a wrapper `<script>` that loads `debug.js` only when `?debug` is in the URL

## MODIFIED Requirements

### Requirement: Application configuration shall use type-safe dataclasses

The framework SHALL provide `AppConfig`, `ServerConfig`, and `GenerateConfig` dataclasses with validated fields and sensible defaults. `AppConfig` SHALL contain settings shared between browser and server environments (including `app_package` for server-side use). `ServerConfig` and `GenerateConfig` are internal types used by CLI functions, not part of the public API surface. `AppConfig` is the sole developer-facing configuration class.

#### Scenario: Creating a minimal application configuration
- **WHEN** a developer creates `AppConfig()` without explicit config
- **THEN** default `AppConfig` values SHALL be used (`base_url="/"`, `dependencies=None`, `assets=None`, `app_package="."`, `profile=False`, `hydrate=True`, `version=None`, `serve_all_deps=True`, `scripts` shall be an empty list, default `field(default_factory=list)`)
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
