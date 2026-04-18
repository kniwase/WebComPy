## ADDED Requirements

### Requirement: E2E tests shall run against both serving modes
E2E browser tests SHALL run the same assertions against both the dev server (`webcompy start --dev`) and the static site (`webcompy generate` served via HTTP). This ensures that both serving modes produce functionally equivalent output. Test authors SHALL write test functions once using a unified `app_page` fixture that is parametrized by serving mode.

#### Scenario: Running a bootstrap test against both modes
- **WHEN** the `test_app_loads` test is executed
- **THEN** it SHALL run twice: once against the dev server and once against the static site
- **AND** both runs SHALL appear in the pytest output with mode identifiers (e.g., `test_app_loads[dev]` and `test_app_loads[static]`)

#### Scenario: A test fails on static site but passes on dev server
- **WHEN** a regression affects only the static site serving mode
- **THEN** the pytest output SHALL show the failing parametrized variant clearly (e.g., `test_app_loads[static] FAILED`)
- **AND** the dev-server variant SHALL still pass

### Requirement: E2E test app package name shall contain an underscore
The e2e test application package directory SHALL be named `my_app` (containing an underscore), not `app`. This ensures that the wheel filename normalization code path (which converts underscores to underscores per PEP 427) is exercised during e2e tests.

#### Scenario: Generating a static site with an underscore-named app package
- **WHEN** `webcompy generate` is run with `app_package=Path(__file__).parent / "my_app"`
- **THEN** the generated wheel filename SHALL contain `my_app` (not `my-app`)
- **AND** micropip SHALL successfully parse the wheel filename and install the package in the browser

### Requirement: E2E tests shall detect Python exceptions in the browser console
After PyScript initialization completes (indicated by `#webcompy-loading` becoming hidden), tests SHALL be able to assert that no Python tracebacks or exceptions appear in the browser console. This catches errors like micropip package installation failures, import errors, and runtime Python exceptions that would prevent the application from rendering.

#### Scenario: Micropip fails to parse a wheel filename
- **WHEN** a wheel filename violates PEP 427 and micropip raises `InvalidVersion` during installation
- **THEN** the e2e test SHALL detect the Python traceback in the browser console
- **AND** the test SHALL fail with a message identifying the Python exception

#### Scenario: No Python exceptions during normal operation
- **WHEN** the application loads and renders correctly without any Python errors
- **THEN** the console error assertion SHALL pass (no Python tracebacks detected)

### Requirement: Static site generation tests shall remain mode-specific
Tests that validate the static site build output (wheel file integrity, HTML content, file structure) SHALL NOT be parametrized by serving mode, because these properties are specific to the `webcompy generate` output and do not apply to the dev server. These tests SHALL remain in a dedicated test file for static site generation concerns.

#### Scenario: Wheel filename matches HTML URL (static-site-only)
- **WHEN** the static site is generated
- **THEN** the wheel filename assertion SHALL verify that the wheel file name matches the URL referenced in `index.html`
- **AND** this test SHALL appear only once (not parametrized by mode)