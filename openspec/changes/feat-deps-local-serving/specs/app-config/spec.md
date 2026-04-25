# App Configuration — Delta: feat-deps-local-serving

## ADDED Requirements

### Requirement: AppConfig shall include a deps_serving field for controlling pure-Python package delivery
`AppConfig` SHALL include a `deps_serving: Literal["bundled", "local-cdn"] = "bundled"` field. When `"bundled"` (default), pure-Python packages are bundled from local installation. When `"local-cdn"`, pure-Python packages are downloaded from the Pyodide CDN and bundled into the app wheel.

#### Scenario: Default bundled mode
- **WHEN** a developer creates `AppConfig()` without `deps_serving`
- **THEN** pure-Python packages SHALL be bundled from local installation (same as `feat-dependency-bundling`)

#### Scenario: Local-cdn mode
- **WHEN** a developer creates `AppConfig(deps_serving="local-cdn")`
- **THEN** pure-Python packages SHALL be downloaded from the Pyodide CDN
- **AND** transitive dependencies SHALL be resolved via the Pyodide lock `depends` field
- **AND** downloaded packages SHALL be extracted and bundled into the app wheel