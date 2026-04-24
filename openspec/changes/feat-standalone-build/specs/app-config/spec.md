# Application Configuration — Delta: feat-standalone-build

## ADDED Requirements

### Requirement: GenerateConfig and ServerConfig shall include a standalone flag
`GenerateConfig` and `ServerConfig` SHALL include `standalone: bool = False`. When `True`, all PyScript and Pyodide assets are served from the same origin instead of external CDN.

#### Scenario: Enabling standalone mode
- **WHEN** a developer creates `GenerateConfig(standalone=True)` or `ServerConfig(standalone=True)`
- **THEN** the `standalone` flag SHALL be stored as `True`
- **AND** the CLI SHALL download and serve all assets locally