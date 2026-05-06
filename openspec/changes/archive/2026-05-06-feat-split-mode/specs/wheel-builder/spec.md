# Wheel Builder — Delta: feat-split-mode

## ADDED Requirements

### Requirement: The wheel builder shall produce a framework wheel in split mode
When `wheel_mode="split"`, `make_browser_webcompy_wheel()` SHALL produce a PEP 427 wheel containing the webcompy framework source but excluding `webcompy/cli/`. The wheel filename SHALL use a content-derived hash: `webcompy-0+sha.{hash8}-py3-none-any.whl`.

#### Scenario: Building a framework wheel in split mode
- **WHEN** `make_browser_webcompy_wheel()` is called
- **THEN** the resulting wheel SHALL contain `webcompy/app/`, `webcompy/elements/`, `webcompy/reactive/`, etc.
- **AND** the wheel SHALL NOT contain `webcompy/cli/` or any files under `webcompy/cli/`
- **AND** `top_level.txt` SHALL list `webcompy`
- **AND** the wheel filename SHALL follow the content-hash pattern `webcompy-0+sha.{hash8}-py3-none-any.whl`

#### Scenario: Framework wheel hash changes on version upgrade
- **WHEN** a new version of webcompy is released and `make_browser_webcompy_wheel()` is called again
- **THEN** the wheel filename SHALL change, invalidating browser caches for all users

### Requirement: The app wheel in split mode shall bundle the app and all dependencies
When `wheel_mode="split"`, `make_webcompy_app_package()` SHALL produce a wheel containing the app package, its assets, and ALL pure-Python dependencies (both locally-installed and CDN-downloaded). The wheel filename SHALL use content-hash: `{app_name}-0+sha.{hash8}-py3-none-any.whl`. Dependencies are NOT split into individual wheels.

#### Scenario: Building app wheel in split mode
- **WHEN** `make_webcompy_app_package()` is called with `wheel_mode="split"`
- **THEN** the resulting wheel SHALL contain the app package, its assets, and all bundled dependencies
- **AND** the wheel SHALL NOT contain `webcompy/` (framework is a separate wheel)
- **AND** the filename SHALL follow the content-hash pattern
