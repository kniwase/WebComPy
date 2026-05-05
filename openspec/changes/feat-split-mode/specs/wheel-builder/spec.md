# Wheel Builder — Delta: feat-split-mode

## ADDED Requirements

### Requirement: The wheel builder shall produce a browser-only framework wheel in split mode
When `wheel_mode="split"`, `make_browser_webcompy_wheel()` SHALL produce a PEP 427 wheel containing the webcompy framework source but excluding `webcompy/cli/`. The wheel filename SHALL be `webcompy-py3-none-any.whl` (stable name, no content-hash).

#### Scenario: Building a browser-only wheel in split mode
- **WHEN** `make_browser_webcompy_wheel()` is called
- **THEN** the resulting wheel SHALL contain `webcompy/app/`, `webcompy/elements/`, `webcompy/reactive/`, etc.
- **AND** the wheel SHALL NOT contain `webcompy/cli/` or any files under `webcompy/cli/`
- **AND** `top_level.txt` SHALL list `webcompy`
- **AND** the wheel filename SHALL be `webcompy-py3-none-any.whl`

### Requirement: The wheel builder shall produce per-dependency wheels in split mode
When `wheel_mode="split"`, each pure-Python dependency SHALL be packaged as a separate wheel using `make_wheel()` with a stable filename `{dep_name}-py3-none-any.whl`. Each dependency wheel SHALL contain only that package and its transitive bundled dependencies.

#### Scenario: Building per-dependency wheels
- **WHEN** `wheel_mode="split"` and there are bundled dependencies `["flask", "httpx"]`
- **THEN** separate wheel files SHALL be produced: `flask-py3-none-any.whl` and `httpx-py3-none-any.whl`
- **AND** each dependency wheel SHALL contain only that package

### Requirement: App wheel in split mode shall retain content-hash
When `wheel_mode="split"`, `make_webcompy_app_package()` SHALL produce an app-only wheel with the existing content-hash filename pattern `{app_name}-0+sha.{hash8}-py3-none-any.whl`. The wheel SHALL contain the app package and its assets, but SHALL NOT contain webcompy framework or dependency packages.

#### Scenario: Building app wheel in split mode
- **WHEN** `make_webcompy_app_package()` is called with `wheel_mode="split"`
- **THEN** the resulting wheel SHALL contain only the app package
- **AND** the wheel SHALL NOT contain `webcompy/` or dependency directories
- **AND** the filename SHALL follow the content-hash pattern
