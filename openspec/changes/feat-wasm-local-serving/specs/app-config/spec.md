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
- **AND** they SHALL be served from `/_webcompy-assets/packages/` via local URLs in `py-config.packages`