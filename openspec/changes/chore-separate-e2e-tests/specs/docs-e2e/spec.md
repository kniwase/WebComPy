## MODIFIED Requirements

### Requirement: Docs E2E tests shall run in a separate test directory with dedicated fixtures
Docs_app E2E tests SHALL reside in `e2e/docs/`, separate from the framework-level E2E tests in `e2e/core/`. Both suites SHALL share a root conftest at `e2e/conftest.py` that enforces the `WEBCOMPY_RUN_E2E=1` opt-in guard (as defined in the `test-execution-paths` spec Requirement "E2E test collection shall require opt-in via environment variable"). The `e2e/docs/conftest.py` SHALL provide the following fixtures: `docs_prod_server` (starts the production server on port 8081), `docs_static_site` (generates and serves the static site), `docs_static_server` (serves the generated static site on a random port), `docs_server_url` (yields the base URL for the current serving mode), `docs_app_page` (navigates to the root URL and waits for PyScript initialization, keeping the page loaded for subsequent navigation), `docs_page_on` (returns a callable that navigates to a given path and waits for initialization, creating a fresh page each time), `console_errors` (collects browser console error messages), and `assert_no_python_errors` (asserts no Python tracebacks appear in console errors after test execution).

#### Scenario: Running docs E2E tests
- **WHEN** a developer runs `scripts/run-e2e-tests.sh docs-home` (or `WEBCOMPY_RUN_E2E=1 pytest e2e/docs/`)
- **THEN** the docs_app production server SHALL start on port 8081
- **AND** the static site SHALL be generated and served on a random port
- **AND** tests SHALL run against both serving modes by default

#### Scenario: Using docs_app_page for navigation tests
- **WHEN** a test uses the `docs_app_page` fixture
- **THEN** the fixture SHALL navigate to the root URL and wait for PyScript initialization to complete
- **AND** the same browser page SHALL be reused for subsequent navigation within the test (no repeated PyScript initialization)

#### Scenario: Using docs_page_on for per-page navigation
- **WHEN** a test calls `docs_page_on("/sample/helloworld")`
- **THEN** the fixture SHALL navigate to the specified path and wait for PyScript initialization to complete
- **AND** each call SHALL wait for `#webcompy-loading` to become hidden and `#webcompy-app` to become visible

### Requirement: Docs E2E tests shall verify page loads without console errors
Each page in the docs_app SHALL load completely without Python tracebacks or JavaScript errors in the browser console. The `assert_no_python_errors` fixture SHALL detect tracebacks containing "Traceback (most recent call last):", "micropip._vendored.", or "pyodide." patterns. These patterns are intentionally broad to catch Pyodide internal errors that may appear as `pyodide.` prefixed messages, matching the pattern used in the existing `e2e/core/conftest.py`.

#### Scenario: Loading the home page without errors
- **WHEN** a test navigates to `/` and waits for PyScript initialization
- **THEN** no Python tracebacks SHALL appear in the browser console
- **AND** the page SHALL render correctly

#### Scenario: Loading the FizzBuzz demo without errors
- **WHEN** a test navigates to `/sample/fizzbuzz` and waits for PyScript initialization
- **THEN** no Python tracebacks SHALL appear in the browser console

### Requirement: Each docs page shall have a dedicated test file
Each route in the docs_app SHALL have a dedicated test file in `e2e/docs/`. Test files SHALL be named `test_<page_name>.py` matching the route path (e.g., `test_home.py` for `/`, `test_fizzbuzz.py` for `/sample/fizzbuzz`).

#### Scenario: Test file organization
- **WHEN** the docs_app has routes `/`, `/documents`, `/sample/helloworld`, `/sample/fizzbuzz`, `/sample/todo`, `/sample/matplotlib`, `/sample/fetch`
- **THEN** there SHALL be test files `test_home.py`, `test_documents.py`, `test_helloworld.py`, `test_fizzbuzz.py`, `test_todo.py`, `test_matplotlib.py`, and `test_fetch.py` in `e2e/docs/`
