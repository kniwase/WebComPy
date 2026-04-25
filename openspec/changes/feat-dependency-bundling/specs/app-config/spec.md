# Application Configuration — Delta: feat-dependency-bundling

## ADDED Requirements

### Requirement: AppConfig shall include a version field for wheel metadata
`AppConfig` SHALL include a `version: str | None = None` field. When provided, the wheel METADATA SHALL use this version string. When `None`, a timestamp-based fallback SHALL be used. The wheel URL SHALL NOT include the version — it remains stable for browser caching.

#### Scenario: Providing an explicit version
- **WHEN** a developer creates `AppConfig(version="1.0.0")`
- **THEN** the wheel METADATA SHALL include `Version: 1.0.0`
- **AND** the wheel URL SHALL remain stable without a version suffix

#### Scenario: Omitting the version
- **WHEN** a developer creates `AppConfig()` without a `version` parameter
- **THEN** a timestamp-based fallback SHALL be used for wheel METADATA version
- **AND** the wheel URL SHALL remain stable without a version suffix

### Requirement: Pure-Python packages shall always be served locally from the WebComPy server
Pure-Python packages SHALL always be bundled into the app wheel and served from the WebComPy server, regardless of whether they are available in the Pyodide CDN. Only WASM packages (which cannot be bundled) SHALL be loaded from the Pyodide CDN. There is no configuration option to change this behavior.

#### Scenario: Pure-Python package available in Pyodide CDN
- **WHEN** a dependency (e.g., `httpx`) is a pure-Python package available in the Pyodide CDN
- **THEN** it SHALL be bundled into the app wheel and served from the WebComPy server
- **AND** it SHALL NOT appear in `py-config.packages`

#### Scenario: WASM-only dependency
- **WHEN** a dependency (e.g., `numpy`) is a WASM package in Pyodide
- **THEN** the dependency SHALL be loaded from the Pyodide CDN because it cannot be bundled as pure Python
- **AND** it SHALL appear in `py-config.packages` as a plain package name