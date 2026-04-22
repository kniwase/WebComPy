# Application Configuration — Delta: feat-hydration-measurement

## ADDED Requirements

### Requirement: AppConfig shall include a profile field for profiling control
`AppConfig` SHALL include a `profile: bool = False` field. When `True`, the generated HTML SHALL include profiling bootstrap code that captures `pyscript_ready` at the start of the PyScript execution. The `profile` parameter is also accepted directly by `WebComPyApp.__init__()` and syncs to `AppConfig.profile` when provided.

#### Scenario: Configuring profiling via AppConfig
- **WHEN** a developer creates `AppConfig(profile=True)`
- **THEN** `profile` SHALL be stored as `True`
- **AND** the generated HTML SHALL include profiling bootstrap code

#### Scenario: Profile parameter on WebComPyApp overrides AppConfig
- **WHEN** a developer creates `WebComPyApp(..., profile=True, config=AppConfig(profile=False))`
- **THEN** the explicit `profile=True` parameter SHALL take precedence over `config.profile`

#### Scenario: Profile defaults from AppConfig
- **WHEN** a developer creates `WebComPyApp(..., config=AppConfig(profile=True))` without an explicit `profile` parameter
- **THEN** `config.profile` SHALL be used as the effective value