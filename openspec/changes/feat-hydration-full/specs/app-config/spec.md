# Application Configuration — Delta: feat-hydration-full

## ADDED Requirements

### Requirement: AppConfig shall include a hydrate field for hydration control
`AppConfig` SHALL include a `hydrate: bool = True` field. When `True`, the browser-side app initialization SHALL use full hydration mode, adopting prerendered DOM nodes instead of creating new ones. When `False`, all DOM nodes SHALL be created from scratch. `WebComPyApp.__init__()` SHALL accept a `hydrate` parameter directly, reading from `config.hydrate` as fallback when not explicitly provided.

#### Scenario: Configuring hydration via AppConfig
- **WHEN** a developer creates `AppConfig(hydrate=False)`
- **THEN** `hydrate` SHALL be stored as `False`
- **AND** the browser-side app SHALL create all DOM nodes from scratch

#### Scenario: Hydrate parameter on WebComPyApp overrides AppConfig
- **WHEN** a developer creates `WebComPyApp(..., hydrate=False, config=AppConfig(hydrate=True))`
- **THEN** the explicit `hydrate=False` parameter SHALL take precedence over `config.hydrate`

#### Scenario: Hydrate defaults from AppConfig
- **WHEN** a developer creates `WebComPyApp(..., config=AppConfig(hydrate=True))` without an explicit `hydrate` parameter
- **THEN** `config.hydrate` SHALL be used as the effective value