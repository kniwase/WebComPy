# E2E Testing

## Purpose

End-to-end browser testing validates that WebComPy applications load and render correctly in a real browser environment, across both serving modes (production server and static site). This ensures that the full pipeline — from wheel packaging to PyScript initialization to component rendering — works correctly for end users, catching integration bugs that unit tests cannot detect.

## Requirements

### Requirement: E2E tests shall run against both serving modes
E2E browser tests SHALL run the same assertions against both the production server (`webcompy start`, without `--dev`) and the static site (`webcompy generate` served via HTTP). Test authors SHALL write test functions once using a unified `app_page` fixture. The serving mode SHALL be selectable via a pytest CLI option (`--serving-mode`) or environment variable so that CI can execute each mode in a separate matrix job. When no mode is specified, the test suite SHALL default to running both modes for backward compatibility.

#### Scenario: Running a bootstrap test against both modes
- **WHEN** the `test_app_loads` test is executed
- **THEN** it SHALL run twice: once against the production server and once against the static site
- **AND** both runs SHALL appear in the pytest output with mode identifiers (e.g., `test_app_loads[prod]` and `test_app_loads[static]`)

#### Scenario: A test fails on static site but passes on production server
- **WHEN** a regression affects only the static site serving mode
- **THEN** the pytest output SHALL show the failing parametrized variant clearly (e.g., `test_app_loads[static] FAILED`)
- **AND** the production-server variant SHALL still pass

#### Scenario: CI matrix runs prod and static in parallel
- **WHEN** the CI workflow defines a matrix with `serving_mode: [prod, static]`
- **THEN** each matrix job SHALL invoke pytest with `--serving-mode=${{ matrix.serving_mode }}`
- **AND** each job SHALL run only the tests for the specified mode

#### Scenario: Local run with default behavior
- **WHEN** a developer runs `pytest tests/e2e/` without `--serving-mode`
- **THEN** pytest SHALL run each test twice: once for `prod` and once for `static`
- **AND** both runs SHALL appear in the pytest output with mode identifiers

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
Tests that validate the static site build output (wheel file integrity, HTML content, file structure) SHALL NOT be parametrized by serving mode, because these properties are specific to the `webcompy generate` output and do not apply to the production server. These tests SHALL remain in a dedicated test file for static site generation concerns.

#### Scenario: Wheel filename matches HTML URL (static-site-only)
- **WHEN** the static site is generated
- **THEN** the wheel filename assertion SHALL verify that the wheel file name matches the URL referenced in `index.html`
- **AND** this test SHALL appear only once (not parametrized by mode)

### Requirement: E2E tests shall support standalone mode selection via CLI
The E2E test configuration SHALL accept a `--serving-mode` pytest CLI option with values `prod` or `static`. When provided, the `serving_mode` fixture SHALL yield only the requested mode, bypassing parametrize.

#### Scenario: Running only static mode tests
- **WHEN** pytest is invoked with `--serving-mode=static`
- **THEN** each E2E test SHALL execute exactly once against the static site
- **AND** the test output SHALL show `test_app_loads` (not `[static]` suffix) because parametrize is disabled

### Requirement: Docs_app E2E tests shall support the same serving mode configuration as the framework E2E tests
The `tests/e2e_docs/` test suite SHALL support the same `--serving-mode` CLI option and parametrize pattern as the `tests/e2e/` suite (as defined in the existing `e2e-testing` spec Requirement "E2E tests shall run against both serving modes"), allowing developers to run tests against the production server, the static site, or both. When no mode is specified, tests SHALL run against both modes. When `--serving-mode=prod` or `--serving-mode=static` is provided, tests SHALL run only against the specified mode.

#### Scenario: Running docs_app E2E tests with both modes
- **WHEN** a developer runs `pytest tests/e2e_docs/` without `--serving-mode`
- **THEN** each test SHALL run twice: once against the docs_app production server and once against the static site
- **AND** both runs SHALL appear in the pytest output with mode identifiers

#### Scenario: Running docs_app E2E tests in CI with a single mode
- **WHEN** the CI workflow runs `pytest tests/e2e_docs/ --serving-mode=prod`
- **THEN** each test SHALL execute exactly once against the production server