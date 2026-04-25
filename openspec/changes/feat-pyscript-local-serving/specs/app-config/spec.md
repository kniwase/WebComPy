# Application Configuration — Delta: feat-pyscript-local-serving

## ADDED Requirements

### Requirement: GenerateConfig and ServerConfig shall include runtime_serving field
`GenerateConfig` and `ServerConfig` SHALL include a `runtime_serving: Literal["cdn", "local"] = "cdn"` field. When `"local"`, PyScript and Pyodide runtime assets are downloaded at build time and served from the same origin instead of external CDN.

#### Scenario: Enabling runtime local serving in config
- **WHEN** a developer creates `GenerateConfig(runtime_serving="local")` or `ServerConfig(runtime_serving="local")`
- **THEN** all runtime assets SHALL be downloaded and served locally