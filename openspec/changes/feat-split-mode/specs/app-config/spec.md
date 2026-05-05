# App Configuration — Delta: feat-split-mode

## ADDED Requirements

### Requirement: AppConfig shall include a wheel_mode field for controlling wheel bundling strategy
`AppConfig` SHALL include a `wheel_mode: Literal["bundled", "split"] = "bundled"` field. When `"bundled"` (default), all code is combined into a single wheel. When `"split"`, separate wheels are produced for the webcompy framework, each pure-Python dependency, and the app.

#### Scenario: Default bundled mode
- **WHEN** a developer creates `AppConfig()` without `wheel_mode`
- **THEN** a single bundled wheel SHALL be produced containing webcompy (excl. cli), app code, and pure-Python dependencies

#### Scenario: Split mode
- **WHEN** a developer creates `AppConfig(wheel_mode="split")`
- **THEN** separate wheels SHALL be produced for webcompy framework, each pure-Python dependency, and the app
- **AND** each wheel SHALL be served at a stable URL under `/_webcompy-app-package/`
- **AND** all wheel URLs SHALL be listed in `py-config.packages`

#### Scenario: Split mode with serve_all_deps=True
- **WHEN** `wheel_mode="split"` and `serve_all_deps=True` (default)
- **THEN** CDN-downloaded pure-Python packages SHALL each get their own wheel
- **AND** locally-bundled pure-Python packages SHALL each get their own wheel

#### Scenario: Split mode with serve_all_deps=False
- **WHEN** `wheel_mode="split"` and `serve_all_deps=False`
- **THEN** CDN-available pure-Python package names SHALL appear in `py-config.packages` as plain names
- **AND** only non-CDN pure-Python packages SHALL get their own wheels
