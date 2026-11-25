# Delta: docs-e2e

(Base: applies after `feat-docs-home-refresh-getting-started` and `feat-docs-examples`'s docs-site-documents delta.)

## MODIFIED Requirements

### Requirement: Each docs page shall have a dedicated test file
Each route in the docs_app SHALL have a dedicated test file in `e2e/docs/`. Test files SHALL be named `test_<page_name>.py` matching the route path (e.g., `test_home.py` for `/`, `test_examples_todo.py` for `/documents/examples/todo`).

#### Scenario: Test file organization
- **WHEN** the docs_app has routes `/`, `/documents`, `/documents/examples/hello-world`, `/documents/examples/todo`, `/documents/examples/matplotlib`, `/documents/examples/http-fetch`
- **THEN** there SHALL be correspondingly named test files in `e2e/docs/`

### Requirement: Docs E2E tests shall verify SPA navigation
Tests SHALL verify that client-side routing works by clicking navigation links and verifying that the URL and page content change correctly. Navigation tests SHALL use the `docs_app_page` fixture (which keeps the page loaded, avoiding repeated PyScript initialization) for forward navigation, and the `docs_page_on` fixture for direct URL navigation.

#### Scenario: Navigating from Home to HelloWorld demo
- **WHEN** a test on the home page clicks the "Documents" dropdown toggle and then the "Hello World" example link
- **THEN** the URL SHALL change to `/documents/examples/hello-world`
- **AND** the example heading SHALL be visible
- **AND** no Python tracebacks SHALL appear in the browser console

#### Scenario: Navigating back to Home
- **WHEN** a test navigates to `/documents/examples/hello-world` and then clicks the "Home" link
- **THEN** the URL SHALL change to `/`
- **AND** the "Build Frontend in Python" hero heading SHALL be visible

#### Scenario: Navigating from the Home hero to Getting Started
- **WHEN** a test on the home page clicks the "Get Started" button
- **THEN** the URL SHALL change to `/documents/getting-started/what-is-webcompy`
- **AND** the page's heading SHALL be visible

## REMOVED Requirements

### Requirement: Docs E2E tests shall verify page content using text and role selectors

**Reason**: the scenarios enumerated here (home "What is WebComPy" heading, FizzBuzz "Add" button) are retired by the Home refresh and the Examples restructure; the requirement's normative selector guidance moves to `docs_e2e_content_selectors` without the stale examples.

**Migration**: see the added `Content-based element location in docs E2E tests` requirement.

### Requirement: Docs E2E tests shall test basic interactivity on demo pages

**Reason**: the `/sample/*` demo pages are replaced by `/documents/examples/*`; the FizzBuzz scenario retires with the demo, and the surviving ToDo/Matplotlib scenarios move under the examples requirement with updated URLs plus a new RPC-middleware mock scenario.

**Migration**: see the added `Example pages shall be tested for demo interactivity` requirement.

### Requirement: Fetch demo test shall be skipped until sample.json is available

**Reason**: obsolete premise — the static data exists (`sample_object.json`, since the typed API client change) and the fetch example is exercised live on both serving modes.

**Migration**: delete the skip marker; `test_examples_http_fetch.py` runs unconditionally.

## ADDED Requirements

### Requirement: Content-based element location in docs E2E tests
Since docs_app is a production site without `data-testid` attributes, tests SHALL locate elements using Playwright's text-based and role-based selectors (e.g., `page.get_by_role()`, `page.locator("h2")`). Tests SHALL NOT require modifications to production component code.

#### Scenario: Verifying the home page heading
- **WHEN** a test navigates to `/`
- **THEN** the test locates the hero via `page.get_by_role("heading", name="Build Frontend in Python", level=1)`

#### Scenario: Verifying a button exists on the Forms example
- **WHEN** a test navigates to `/documents/examples/forms`
- **THEN** the test locates the demo's submit button by role

### Requirement: Example pages shall be tested for demo interactivity
Examples pages with interactive demos SHALL be tested for basic user interactions inside the demo iframe.

#### Scenario: ToDo list Add ToDo button adds an item
- **WHEN** a test navigates to `/documents/examples/todo`, types text in the input, and clicks "Add ToDo"
- **THEN** a new list item appears

#### Scenario: Matplotlib plus button increments the value
- **WHEN** a test navigates to `/documents/examples/matplotlib` and clicks the "+" button
- **THEN** the value display increments

#### Scenario: RPC middleware mock responds without a server
- **WHEN** a test on `/documents/examples/rpc-middleware` clicks the demo's call button
- **THEN** the typed result renders and no failed network request appears in the console
