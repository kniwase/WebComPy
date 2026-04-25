# Wheel Builder — Delta: feat-split-mode

## ADDED Requirements

### Requirement: The wheel builder shall produce a browser-only framework wheel in split mode
When `wheel_mode="split"`, `make_browser_webcompy_wheel()` SHALL produce a PEP 427 wheel containing the webcompy framework source but excluding `webcompy/cli/`. The wheel SHALL be named `webcompy-py3-none-any.whl`.

#### Scenario: Building a browser-only wheel in split mode
- **WHEN** `make_browser_webcompy_wheel()` is called
- **THEN** the resulting wheel SHALL contain `webcompy/app/`, `webcompy/elements/`, `webcompy/reactive/`, etc.
- **AND** the wheel SHALL NOT contain `webcompy/cli/` or any files under `webcompy/cli/`
- **AND** `top_level.txt` SHALL list `webcompy`
- **AND** the wheel filename SHALL be `webcompy-py3-none-any.whl`

### Requirement: The wheel builder shall produce per-dependency wheels in split mode
When `wheel_mode="split"`, each pure-Python dependency SHALL be packaged as a separate wheel named `{dep_name}-py3-none-any.whl`.

#### Scenario: Building per-dependency wheels
- **WHEN** `wheel_mode="split"` and there are bundled dependencies `["flask", "httpx"]`
- **THEN** separate wheel files SHALL be produced: `flask-py3-none-any.whl` and `httpx-py3-none-any.whl`
- **AND** each dependency wheel SHALL contain only that package