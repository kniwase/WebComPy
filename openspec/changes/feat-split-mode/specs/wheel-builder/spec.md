# Wheel Builder — Delta: feat-split-mode

## ADDED Requirements

### Requirement: The wheel builder shall produce a browser-only framework wheel in split mode
When `wheel_mode="split"`, `make_browser_webcompy_wheel()` SHALL produce a PEP 427 wheel containing the webcompy framework source but excluding `webcompy/cli/`. The wheel filename SHALL use a content-derived hash: `webcompy-0+sha.{hash8}-py3-none-any.whl`.

#### Scenario: Building a browser-only wheel in split mode
- **WHEN** `make_browser_webcompy_wheel()` is called
- **THEN** the resulting wheel SHALL contain `webcompy/app/`, `webcompy/elements/`, `webcompy/reactive/`, etc.
- **AND** the wheel SHALL NOT contain `webcompy/cli/` or any files under `webcompy/cli/`
- **AND** `top_level.txt` SHALL list `webcompy`
- **AND** the wheel filename SHALL follow the content-hash pattern `webcompy-0+sha.{hash8}-py3-none-any.whl`

#### Scenario: Framework wheel hash changes on version upgrade
- **WHEN** a new version of webcompy is released and `make_browser_webcompy_wheel()` is called again
- **THEN** the wheel filename SHALL change, invalidating browser caches for all users

### Requirement: The wheel builder shall produce per-dependency wheels in split mode
When `wheel_mode="split"`, each pure-Python dependency SHALL be packaged as a separate wheel using `make_wheel()` and then content-hash renamed. Each dependency wheel filename SHALL be `{dep_name}-0+sha.{hash8}-py3-none-any.whl`.

#### Scenario: Building per-dependency wheels
- **WHEN** `wheel_mode="split"` and there are bundled dependencies `["flask", "httpx"]`
- **THEN** separate content-hashed wheel files SHALL be produced: `flask-0+sha.{hash8}-py3-none-any.whl` and `httpx-0+sha.{hash8}-py3-none-any.whl`
- **AND** each dependency wheel SHALL contain only that package

#### Scenario: Dependency wheel hash changes on version upgrade
- **WHEN** a dependency version changes in the project
- **THEN** the corresponding dependency wheel filename SHALL change, invalidating browser caches

### Requirement: App wheel in split mode shall retain content-hash
When `wheel_mode="split"`, `make_webcompy_app_package()` SHALL produce an app-only wheel with the existing content-hash filename pattern `{app_name}-0+sha.{hash8}-py3-none-any.whl`. The wheel SHALL contain the app package and its assets, but SHALL NOT contain webcompy framework or dependency packages.

#### Scenario: Building app wheel in split mode
- **WHEN** `make_webcompy_app_package()` is called with `wheel_mode="split"`
- **THEN** the resulting wheel SHALL contain only the app package
- **AND** the wheel SHALL NOT contain `webcompy/` or dependency directories
- **AND** the filename SHALL follow the content-hash pattern
