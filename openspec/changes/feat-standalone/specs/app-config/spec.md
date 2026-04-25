# App Configuration — Delta: feat-standalone

## ADDED Requirements

### Requirement: AppConfig shall include a standalone flag for complete offline capability
`AppConfig` SHALL include a `standalone: bool = False` field. When `True`, all local-serving modes are enabled simultaneously: pure-Python packages are downloaded from Pyodide CDN, WASM packages are served locally, and the PyScript/Pyodide runtime is served locally.

#### Scenario: Enabling standalone mode
- **WHEN** a developer creates `AppConfig(standalone=True)`
- **THEN** the equivalent config SHALL be `deps_serving="local-cdn"`, `wasm_serving="local"`, and runtime local serving enabled
- **AND** the build SHALL produce a fully self-contained output with zero external CDN requests

#### Scenario: Individual overrides
- **WHEN** a developer creates `AppConfig(standalone=True, wasm_serving="cdn")`
- **THEN** the explicit `wasm_serving="cdn"` SHALL take precedence over the `standalone` default
- **AND** WASM packages SHALL be loaded from the CDN while other assets are served locally