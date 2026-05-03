# Docs E2E Testing

## Purpose

End-to-end browser testing for the docs_app (WebComPy documentation site) validates that all documentation pages load correctly, interactive demos function properly, and no Python exceptions appear in the browser console. This test suite runs independently from the framework-level E2E tests, with dedicated fixtures and extended timeouts to accommodate heavy browser dependencies like matplotlib.

## Requirements

### Requirement: Docs E2E tests shall run in a separate test directory with dedicated fixtures
Docs_app E2E tests SHALL reside in `tests/e2e_docs/`, separate from the framework-level E2E tests in `tests/e2e/`. The conftest SHALL provide the following fixtures: `docs_prod_server` (starts the production server on port 8081), `docs_static_site` (generates and serves the static site), `docs_static_server` (serves the generated static site on a random port), `docs_server_url` (yields the base URL for the current serving mode), `docs_app_page` (navigates to the root URL and waits for PyScript initialization, keeping the page loaded for subsequent navigation), `docs_page_on` (returns a callable that navigates to a given path and waits for initialization, creating a fresh page each time), `console_errors` (collects browser console error messages), and `assert_no_python_errors` (asserts no Python tracebacks appear in console errors after test execution).

#### Scenario: Running docs E2E tests
- **WHEN** a developer runs `pytest tests/e2e_docs/`
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

### Requirement: Docs E2E tests shall support extended timeout for heavy dependencies
Docs_app uses `dependencies_from="browser"` which requires micropip to download numpy and matplotlib at runtime. The PyScript initialization timeout SHALL be 300 seconds to accommodate this. Individual test files for pages with heavy dependencies (matplotlib) MAY use additional timeouts.

#### Scenario: Loading the matplotlib demo page
- **WHEN** a test navigates to `/sample/matplotlib`
- **THEN** the page SHALL wait up to 300 seconds for PyScript initialization to complete
- **AND** `#webcompy-loading` SHALL become hidden
- **AND** `#webcompy-app` SHALL become visible

#### Scenario: Loading a lightweight page
- **WHEN** a test navigates to `/sample/helloworld`
- **THEN** the page SHALL wait up to 300 seconds for PyScript initialization (same timeout applies to all pages for consistency)

### Requirement: Docs E2E tests shall verify page loads without console errors
Each page in the docs_app SHALL load completely without Python tracebacks or JavaScript errors in the browser console. The `assert_no_python_errors` fixture SHALL detect tracebacks containing "Traceback (most recent call last):", "micropip._vendored.", or "pyodide." patterns. These patterns are intentionally broad to catch Pyodide internal errors that may appear as `pyodide.` prefixed messages, matching the pattern used in the existing `tests/e2e/conftest.py`.

#### Scenario: Loading the home page without errors
- **WHEN** a test navigates to `/` and waits for PyScript initialization
- **THEN** no Python tracebacks SHALL appear in the browser console
- **AND** the page SHALL render correctly

#### Scenario: Loading the FizzBuzz demo without errors
- **WHEN** a test navigates to `/sample/fizzbuzz` and waits for PyScript initialization
- **THEN** no Python tracebacks SHALL appear in the browser console

### Requirement: Docs E2E tests shall verify page content using text and role selectors
Since docs_app is a production site without `data-testid` attributes, tests SHALL locate elements using Playwright's text-based and role-based selectors (e.g., `page.get_by_text()`, `page.get_by_role()`, `page.locator("h2")`). Tests SHALL NOT require modifications to the production component code. The only exception is Bootstrap's `data-bs-toggle` attribute, which is a framework attribute (not a test hook) and MAY be used for dropdown interaction.

#### Scenario: Verifying the home page heading
- **WHEN** a test navigates to `/`
- **THEN** the test SHALL locate the "What is WebComPy" heading using `page.get_by_role("heading", name="What is WebComPy")`

#### Scenario: Verifying a button exists on the FizzBuzz page
- **WHEN** a test navigates to `/sample/fizzbuzz`
- **THEN** the test SHALL locate the "Add" button using `page.get_by_role("button", name="Add")`

### Requirement: Each docs page shall have a dedicated test file
Each route in the docs_app SHALL have a dedicated test file in `tests/e2e_docs/`. Test files SHALL be named `test_<page_name>.py` matching the route path (e.g., `test_home.py` for `/`, `test_fizzbuzz.py` for `/sample/fizzbuzz`).

#### Scenario: Test file organization
- **WHEN** the docs_app has routes `/`, `/documents`, `/sample/helloworld`, `/sample/fizzbuzz`, `/sample/todo`, `/sample/matplotlib`, `/sample/fetch`
- **THEN** there SHALL be test files `test_home.py`, `test_documents.py`, `test_helloworld.py`, `test_fizzbuzz.py`, `test_todo.py`, `test_matplotlib.py`, and `test_fetch.py` in `tests/e2e_docs/`

### Requirement: Docs E2E tests shall test basic interactivity on demo pages
Demo pages with interactive elements (buttons, inputs) SHALL be tested for basic user interactions: clicking buttons updates the displayed state, toggling visibility works, and form inputs respond correctly.

#### Scenario: FizzBuzz Add button adds an item
- **WHEN** a test navigates to `/sample/fizzbuzz` and clicks the "Add" button
- **THEN** the count display SHALL increase by 1

#### Scenario: ToDo list Add ToDo button adds an item
- **WHEN** a test navigates to `/sample/todo`, types text in the input, and clicks "Add ToDo"
- **THEN** a new list item SHALL appear

#### Scenario: Matplotlib plus button increments the value
- **WHEN** a test navigates to `/sample/matplotlib` and clicks the "+" button
- **THEN** the text "Value: 15" SHALL change to "Value: 16"

### Requirement: Fetch demo test shall be skipped until sample.json is available
The `/sample/fetch` page requires a `sample.json` static file that does not yet exist. The test for this page SHALL be marked with `pytest.mark.skip` with a reason explaining the dependency on the static file fix.

#### Scenario: Running the fetch test
- **WHEN** a test run includes `test_fetch.py`
- **THEN** the test SHALL be skipped with a reason referencing the missing `sample.json` static file

### Requirement: Docs E2E tests shall verify SPA navigation
Tests SHALL verify that client-side routing works by clicking navigation links and verifying that the URL and page content change correctly. Navigation tests SHALL use the `docs_app_page` fixture (which keeps the page loaded, avoiding repeated PyScript initialization) for forward navigation, and the `docs_page_on` fixture for direct URL navigation.

#### Scenario: Navigating from Home to HelloWorld demo
- **WHEN** a test on the home page clicks the "Demos" dropdown toggle and then the "HelloWorld" link
- **THEN** the URL SHALL change to `/sample/helloworld`
- **AND** the "HelloWorld" heading SHALL be visible
- **AND** no Python tracebacks SHALL appear in the browser console

#### Scenario: Navigating back to Home
- **WHEN** a test navigates to `/sample/helloworld` and then clicks the "Home" link
- **THEN** the URL SHALL change to `/`
- **AND** the "What is WebComPy" heading SHALL be visible

### Requirement: Docs E2E CI matrix shall cover all test groups
The CI workflow SHALL include a separate matrix entry for docs E2E tests, split into groups for parallel execution. Each group SHALL run against both `prod` and `static` serving modes.

#### Scenario: CI matrix configuration for docs E2E
- **WHEN** the CI workflow runs
- **THEN** there SHALL be matrix entries for `docs-home`, `docs-demos`, `docs-matplotlib`, and `docs-fetch` groups
- **AND** each group SHALL run with `serving_mode: [prod, static]`
- **AND** each group SHALL invoke pytest with the appropriate test files