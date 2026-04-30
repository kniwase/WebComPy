# App Configuration — Delta: feat-wasm-local-serving

## ADDED Requirements

### Requirement: AppConfig shall include a wasm_serving field for controlling WASM package delivery
`AppConfig` SHALL include a `wasm_serving: Literal["cdn", "local"] | None = None` field. When `None` or `"cdn"`, WASM packages are loaded from the Pyodide CDN by package name. When `"local"`, WASM package wheel files are downloaded at build time and served from the same origin. The `None` sentinel enables `standalone` mode (in `feat-standalone`) to distinguish between "unset" (overridden to `"local"`) and "explicitly set to `"cdn"`" (preserved).

#### Scenario: Default CDN mode
- **WHEN** a developer creates `AppConfig()` without `wasm_serving`
- **THEN** WASM packages SHALL be loaded from the Pyodide CDN via `py-config.packages` package names

#### Scenario: Local WASM serving mode
- **WHEN** a developer creates `AppConfig(wasm_serving="local")`
- **THEN** WASM package wheel files SHALL be downloaded from the Pyodide CDN at build time
- **AND** they SHALL be served from `/_webcompy-assets/packages/` via local wheel URLs in `py-config.packages`

## MODIFIED Requirements

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
