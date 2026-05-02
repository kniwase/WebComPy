## Purpose

End-to-end testing of the docs_app documentation site validates that the WebComPy showcase application loads correctly, renders all pages without console errors, and interactive demos function properly. This complements the framework-level E2E tests in `tests/e2e/` by testing a real, production-like application with complex dependencies (matplotlib, micropip) and text/role-based element selection instead of `data-testid` attributes.

## Requirements

### Requirement: Docs E2E tests shall run in a separate test directory
Docs_app E2E tests SHALL reside in `tests/e2e_docs/`, separate from the framework-level E2E tests in `tests/e2e/`. The conftest SHALL provide fixtures for starting the docs_app production server, generating and serving the static site, navigating to pages, and detecting console errors. The test infrastructure SHALL use a separate port (8081) to avoid conflicts with the existing E2E suite.

#### Scenario: Running docs E2E tests
- **WHEN** a developer runs `pytest tests/e2e_docs/`
- **THEN** the docs_app production server SHALL start on port 8081
- **AND** the static site SHALL be generated and served on a random port
- **AND** tests SHALL run against both serving modes by default

#### Scenario: Running docs E2E tests in CI
- **WHEN** the CI workflow runs `pytest` with `--serving-mode=prod` or `--serving-mode=static`
- **THEN** tests SHALL run only against the specified serving mode

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
Each page in the docs_app SHALL load completely without Python tracebacks or JavaScript errors in the browser console. The `assert_no_python_errors` fixture SHALL detect tracebacks containing "Traceback (most recent call last):", "micropip._vendored.", or "pyodide." patterns.

#### Scenario: Loading the home page without errors
- **WHEN** a test navigates to `/` and waits for PyScript initialization
- **THEN** no Python tracebacks SHALL appear in the browser console
- **AND** the page SHALL render correctly

#### Scenario: Loading the FizzBuzz demo without errors
- **WHEN** a test navigates to `/sample/fizzbuzz` and waits for PyScript initialization
- **THEN** no Python tracebacks SHALL appear in the browser console

### Requirement: Docs E2E tests shall verify page content using text and role selectors
Since docs_app is a production site without `data-testid` attributes, tests SHALL locate elements using Playwright's text-based and role-based selectors (e.g., `page.get_by_text()`, `page.get_by_role()`, `page.locator("h2")`). Tests SHALL NOT require modifications to the production component code.

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

### Requirement: Docs E2E CI matrix shall cover all test groups
The CI workflow SHALL include a separate matrix entry for docs E2E tests, split into groups for parallel execution. Each group SHALL run against both `prod` and `static` serving modes.

#### Scenario: CI matrix configuration for docs E2E
- **WHEN** the CI workflow runs
- **THEN** there SHALL be matrix entries for `docs-home`, `docs-demos`, `docs-matplotlib`, and `docs-fetch` groups
- **AND** each group SHALL run with `serving_mode: [prod, static]`
- **AND** each group SHALL invoke pytest with the appropriate test files