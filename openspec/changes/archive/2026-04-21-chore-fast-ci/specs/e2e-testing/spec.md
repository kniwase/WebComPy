## MODIFIED Requirements

### Requirement: E2E tests shall run against both serving modes
E2E browser tests SHALL run the same assertions against both the production server and the static site. Test authors SHALL write test functions once using a unified `app_page` fixture. The serving mode SHALL be selectable via a pytest CLI option (`--serving-mode`) or environment variable so that CI can execute each mode in a separate matrix job. When no mode is specified, the test suite SHALL default to running both modes for backward compatibility.

#### Scenario: CI matrix runs prod and static in parallel
- **WHEN** the CI workflow defines a matrix with `serving_mode: [prod, static]`
- **THEN** each matrix job SHALL invoke pytest with `--serving-mode=${{ matrix.serving_mode }}`
- **AND** each job SHALL run only the tests for the specified mode

#### Scenario: Local run with default behavior
- **WHEN** a developer runs `pytest tests/e2e/` without `--serving-mode`
- **THEN** pytest SHALL run each test twice: once for `prod` and once for `static`
- **AND** both runs SHALL appear in the pytest output with mode identifiers

## ADDED Requirements

### Requirement: E2E tests shall support standalone mode selection via CLI
The E2E test configuration SHALL accept a `--serving-mode` pytest CLI option with values `prod` or `static`. When provided, the `serving_mode` fixture SHALL yield only the requested mode, bypassing parametrize.

#### Scenario: Running only static mode tests
- **WHEN** pytest is invoked with `--serving-mode=static`
- **THEN** each E2E test SHALL execute exactly once against the static site
- **AND** the test output SHALL show `test_app_loads` (not `[static]` suffix) because parametrize is disabled
