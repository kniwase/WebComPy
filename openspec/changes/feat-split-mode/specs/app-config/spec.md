# App Configuration — Delta: feat-split-mode

## ADDED Requirements

### Requirement: AppConfig shall include a wheel_mode field for controlling wheel bundling strategy
`AppConfig` SHALL include a `wheel_mode: Literal["bundled", "split"] = "bundled"` field. When `"bundled"` (default), all code is combined into a single wheel. When `"split"`, two wheels are produced: a framework wheel (webcompy, excl. cli/) and an app wheel (app code + all pure-Python dependencies bundled together).

#### Scenario: Default bundled mode
- **WHEN** a developer creates `AppConfig()` without `wheel_mode`
- **THEN** a single bundled wheel SHALL be produced containing webcompy (excl. cli), app code, and pure-Python dependencies

#### Scenario: Split mode
- **WHEN** a developer creates `AppConfig(wheel_mode="split")`
- **THEN** two wheels SHALL be produced: framework wheel and app wheel (with all deps bundled)
- **AND** both wheel URLs SHALL be listed in `py-config.packages`
