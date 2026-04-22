# Application Configuration — Delta: feat-wheel-split

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