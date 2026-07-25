# Test Execution Paths

## Purpose

WebComPy's unit tests and E2E tests use structurally distinct execution paths so that the two suites cannot accidentally be conflated. Unit tests are the default pytest discovery target and run with no flags; E2E tests live in a physically separate directory, require an opt-in environment variable, and are invoked through a canonical shell script. This separation prevents accidental direct invocation of E2E tests (which would skip port allocation, browser fixtures, and console-log capture) and ensures that plain `uv run pytest` always runs only the fast unit suite.

## Requirements

### Requirement: Unit tests shall be the default pytest discovery target

Unit tests SHALL reside in `tests/` and SHALL be the default discovery target when pytest is invoked without explicit path arguments. The `pyproject.toml` `[tool.pytest.ini_options]` SHALL declare `testpaths = ["tests"]` so that `uv run pytest` (no arguments) discovers only unit tests. E2E test directories SHALL NOT be nested under `tests/`.

#### Scenario: Running unit tests with no arguments

- **WHEN** a developer runs `uv run pytest` without any path arguments
- **THEN** pytest SHALL discover only test files under `tests/`
- **AND** no E2E tests SHALL be collected or executed

#### Scenario: Running a specific unit test file

- **WHEN** a developer runs `uv run pytest tests/test_signal.py`
- **THEN** only the specified unit test file SHALL run
- **AND** no E2E tests SHALL be collected

### Requirement: E2E tests shall reside in a physically separate directory

E2E tests SHALL reside under a top-level `e2e/` directory, physically separate from the unit test directory `tests/`. Framework-level E2E tests SHALL reside in `e2e/core/`. Docs_app E2E tests SHALL reside in `e2e/docs/`. The `e2e/` directory SHALL NOT be listed in `pyproject.toml` `testpaths`, ensuring that default pytest discovery never collects E2E tests.

#### Scenario: E2E tests are not discovered by default

- **WHEN** a developer runs `uv run pytest` without any path arguments
- **THEN** pytest SHALL NOT discover or collect any files under `e2e/`
- **AND** the test run SHALL complete without attempting any browser or server setup

#### Scenario: E2E directory structure

- **WHEN** the repository layout is inspected
- **THEN** framework E2E tests SHALL be located at `e2e/core/test_*.py`
- **AND** docs_app E2E tests SHALL be located at `e2e/docs/test_*.py`
- **AND** a root conftest SHALL exist at `e2e/conftest.py` enforcing the opt-in guard

### Requirement: E2E test collection shall require opt-in via environment variable

E2E tests SHALL require an opt-in environment variable `WEBCOMPY_RUN_E2E=1` to be set before collection proceeds. When pytest collects any test under `e2e/` and the environment variable is not set to `1`, collection SHALL abort with a `pytest.UsageError` before any test fixture is initialized. The error message SHALL direct the user to `scripts/run-e2e-tests.sh` as the canonical entry point and SHALL mention the `WEBCOMPY_RUN_E2E=1` environment variable as an alternative for advanced direct invocation. No browser SHALL be launched and no server SHALL be started when the guard aborts.

#### Scenario: Direct pytest invocation without opt-in

- **WHEN** a developer runs `uv run pytest e2e/` without setting `WEBCOMPY_RUN_E2E`
- **THEN** pytest SHALL abort collection with a `pytest.UsageError`
- **AND** the error message SHALL mention `scripts/run-e2e-tests.sh`
- **AND** the error message SHALL mention the `WEBCOMPY_RUN_E2E=1` environment variable
- **AND** no browser shall be launched and no server shall be started

#### Scenario: Direct pytest invocation with opt-in

- **WHEN** a developer runs `WEBCOMPY_RUN_E2E=1 uv run pytest e2e/core/test_bootstrap.py`
- **THEN** collection SHALL proceed normally
- **AND** the existing E2E fixtures (`prod_server`, `static_site`, etc.) SHALL function as before

### Requirement: scripts/run-e2e-tests.sh shall be the canonical E2E entry point

The `scripts/run-e2e-tests.sh` script SHALL be the canonical entry point for running E2E tests. The script SHALL set `WEBCOMPY_RUN_E2E=1` in the environment of every pytest invocation it spawns, so that the opt-in guard passes automatically. The script SHALL continue to accept group names, `--serving-mode`, `--console-level`, `--console-file-level`, and `--parallel` options as before. The script SHALL reference the new `e2e/core/` and `e2e/docs/` paths in its group definitions.

#### Scenario: Running E2E tests via the script

- **WHEN** a developer runs `scripts/run-e2e-tests.sh components`
- **THEN** the script SHALL set `WEBCOMPY_RUN_E2E=1` in the pytest subprocess environment
- **AND** the specified group SHALL run against both `prod` and `static` serving modes
- **AND** console logs SHALL be captured as before

#### Scenario: Running all E2E groups via the script

- **WHEN** a developer runs `scripts/run-e2e-tests.sh` without arguments
- **THEN** all groups (core + docs) SHALL run
- **AND** the opt-in guard SHALL pass for every subprocess invocation

### Requirement: Conformance harness shall run in the unit-test tier

The GFM conformance harness (`tests/conformance/`) SHALL be collected by the default `pytest tests/` invocation without browser, real-time network access, or the `WEBCOMPY_RUN_E2E` opt-in. The harness MAY fetch the spec.txt once into a local cache (tests/conformance/.tmp/, gitignored) on first use; subsequent runs SHALL use the cache. Only cross-environment parity scenarios involving a real browser SHALL live in the E2E tier.

#### Scenario: Default discovery includes conformance suite

- **WHEN** `uv run python -m pytest tests/` runs without any environment flags
- **THEN** the GFM conformance examples SHALL be collected and executed (using the cached spec.txt if available)

#### Scenario: Browser parity scenario is E2E-gated

- **WHEN** the HTML-parser parity scenario runs
- **THEN** it SHALL execute only via the E2E entry point (`scripts/run-e2e-tests.sh`), as part of an existing or new E2E group
