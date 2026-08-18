## ADDED Requirements

### Requirement: Build configuration shall provide a resource transfer mode setting

`WebComPyBuildConfig` SHALL provide a resource transfer mode field (e.g., `resource_transfer`) selecting how resources are embedded into hydration payloads during SSG. The field SHALL accept at least `"used"` (default: each page's payload contains only the resources that page's render context loaded) and `"all-text"` (every generated page's payload contains every allow-listed text resource). Invalid values SHALL be rejected at configuration time with a clear error. The field SHALL NOT affect the dev/prod server, which always uses per-context ("used") transfer.

#### Scenario: Default mode is per-context transfer
- **WHEN** a project configuration does not specify a resource transfer mode
- **THEN** the mode SHALL default to `"used"`
- **AND** each generated page's payload SHALL contain only resources that page loaded

#### Scenario: Opting into full text-resource transfer
- **WHEN** a project configuration sets the resource transfer mode to `"all-text"`
- **THEN** SSG SHALL embed every allow-listed text resource in every generated page's payload

#### Scenario: Invalid mode rejected
- **WHEN** a project configuration sets the resource transfer mode to an unsupported value
- **THEN** configuration validation SHALL raise an error naming the invalid value and the supported modes
