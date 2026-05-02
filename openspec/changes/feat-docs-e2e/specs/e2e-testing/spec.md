## ADDED Requirements

### Requirement: Docs_app E2E tests shall support the same serving mode configuration as the framework E2E tests
The `tests/e2e_docs/` test suite SHALL support the same `--serving-mode` CLI option and parametrize pattern as the `tests/e2e/` suite (as defined in the existing `e2e-testing` spec Requirement "E2E tests shall support serving mode parametrization"), allowing developers to run tests against the production server, the static site, or both. When no mode is specified, tests SHALL run against both modes. When `--serving-mode=prod` or `--serving-mode=static` is provided, tests SHALL run only against the specified mode.

#### Scenario: Running docs_app E2E tests with both modes
- **WHEN** a developer runs `pytest tests/e2e_docs/` without `--serving-mode`
- **THEN** each test SHALL run twice: once against the docs_app production server and once against the static site
- **AND** both runs SHALL appear in the pytest output with mode identifiers

#### Scenario: Running docs_app E2E tests in CI with a single mode
- **WHEN** the CI workflow runs `pytest tests/e2e_docs/ --serving-mode=prod`
- **THEN** each test SHALL execute exactly once against the production server
