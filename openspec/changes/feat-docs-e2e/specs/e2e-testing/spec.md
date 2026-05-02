## MODIFIED Requirements

### Requirement: E2E tests shall run against both serving modes
E2E browser tests SHALL run the same assertions against both the production server (`webcompy start`, without `--dev`) and the static site (`webcompy generate` served via HTTP). Test authors SHALL write test functions once using a unified `app_page` fixture. The serving mode SHALL be selectable via a pytest CLI option (`--serving-mode`) or environment variable so that CI can execute each mode in a separate matrix job. When no mode is specified, the test suite SHALL default to running both modes for backward compatibility. This requirement applies to both the `tests/e2e/` suite (my_app) and the `tests/e2e_docs/` suite (docs_app).

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