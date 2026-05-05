## MODIFIED Requirements

### Requirement: The app wheel shall bundle webcompy (excluding cli) and bundled dependencies
`make_webcompy_app_package()` SHALL produce a single PEP 427 wheel containing the webcompy framework source (excluding `webcompy/cli/`), the application package, and any bundled pure-Python dependencies (i.e., packages not available from the Pyodide CDN). The wheel filename SHALL include a content-derived hash for cache busting (see Content-hash wheel filename requirement). `make_browser_webcompy_wheel()` SHALL NOT exist — webcompy is bundled inside the app wheel.

#### Scenario: Building an app wheel with webcompy bundled
- **WHEN** `make_webcompy_app_package()` is called
- **THEN** the resulting wheel SHALL contain `webcompy/app/`, `webcompy/elements/`, `webcompy/reactive/`, etc.
- **AND** the wheel SHALL NOT contain `webcompy/cli/` or any files under `webcompy/cli/`
- **AND** `top_level.txt` SHALL list `webcompy` and the app name
- **AND** the wheel filename SHALL follow the content-hash pattern `{app_name}-0+sha.{hash8}-py3-none-any.whl`

#### Scenario: Building an app wheel without bundled dependencies
- **WHEN** `make_webcompy_app_package(..., bundled_deps=None)` is called
- **THEN** the resulting wheel SHALL contain webcompy (excl. cli) and the app package only
- **AND** the wheel filename SHALL follow the content-hash pattern

#### Scenario: Building an app wheel with a single-file module dependency
- **WHEN** a bundled dependency extracted from a CDN wheel is a single `.py` file module (no `__init__.py`, just a top-level `.py` file, e.g., `six.py`)
- **THEN** the wheel SHALL include that `.py` file at the wheel root level (e.g., `six.py`, not `six/six.py`)
- **AND** `top_level.txt` SHALL list the module name alongside other top-level packages
- **AND** importing that module SHALL work after PyScript loads the wheel
