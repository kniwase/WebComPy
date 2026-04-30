# App Configuration — Delta: feat-wasm-local-serving

## ADDED Requirements

### Requirement: AppConfig shall include a wasm_serving field for controlling WASM package delivery
`AppConfig` SHALL include a `wasm_serving: Literal["cdn", "local"] = "cdn"` field. When `"cdn"` (default), WASM packages are loaded from the Pyodide CDN by package name. When `"local"`, WASM package wheel files are downloaded at build time and served from the same origin.

#### Scenario: Default CDN mode
- **WHEN** a developer creates `AppConfig()` without `wasm_serving`
- **THEN** WASM packages SHALL be loaded from the Pyodide CDN via `py-config.packages` package names

#### Scenario: Local WASM serving mode
- **WHEN** a developer creates `AppConfig(wasm_serving="local")`
- **THEN** WASM package wheel files SHALL be downloaded from the Pyodide CDN at build time
- **AND** they SHALL be served from `/_webcompy-assets/packages/` via local wheel URLs in `py-config.packages`

## MODIFIED Requirements

### Requirement: CLI flags shall override wasm_serving
The `start` and `generate` CLI subcommands SHALL accept `--wasm-serving` (sets `wasm_serving="local"`) and `--no-wasm-serving` (sets `wasm_serving="cdn"`) flags that override `AppConfig.wasm_serving`.

#### Scenario: Overriding with --wasm-serving
- **WHEN** a developer runs `python -m webcompy start --dev --wasm-serving`
- **THEN** `wasm_serving` SHALL be `"local"` for the session
- **AND** WASM packages SHALL be downloaded and served locally

#### Scenario: Overriding with --no-wasm-serving
- **WHEN** a developer runs `python -m webcompy generate --no-wasm-serving`
- **THEN** `wasm_serving` SHALL be `"cdn"` for the session
- **AND** WASM packages SHALL be loaded from the Pyodide CDN by name