## MODIFIED Requirements

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
- **WHEN** a developer runs `scripts/run-e2e-tests.sh` without `--serving-mode` (or `WEBCOMPY_RUN_E2E=1 pytest e2e/core/`)
- **THEN** pytest SHALL run each test twice: once for `prod` and once for `static`
- **AND** both runs SHALL appear in the pytest output with mode identifiers

### Requirement: Docs_app E2E tests shall support the same serving mode configuration as the framework E2E tests
The `e2e/docs/` test suite SHALL support the same `--serving-mode` CLI option and parametrize pattern as the `e2e/core/` suite (as defined in the existing `e2e-testing` spec Requirement "E2E tests shall run against both serving modes"), allowing developers to run tests against the production server, the static site, or both. When no mode is specified, tests SHALL run against both modes. When `--serving-mode=prod` or `--serving-mode=static` is provided, tests SHALL run only against the specified mode.

#### Scenario: Running docs_app E2E tests with both modes
- **WHEN** a developer runs `scripts/run-e2e-tests.sh docs-home` without `--serving-mode` (or `WEBCOMPY_RUN_E2E=1 pytest e2e/docs/`)
- **THEN** each test SHALL run twice: once against the docs_app production server and once against the static site
- **AND** both runs SHALL appear in the pytest output with mode identifiers

#### Scenario: Running docs_app E2E tests in CI with a single mode
- **WHEN** the CI workflow runs `scripts/run-e2e-tests.sh docs-home --serving-mode=prod`
- **THEN** each test SHALL execute exactly once against the production server
