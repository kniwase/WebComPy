# Delta: docs-e2e

## MODIFIED Requirements

### Requirement: Docs E2E tests shall verify page content using text and role selectors
Since docs_app is a production site without `data-testid` attributes, tests SHALL locate elements using Playwright's text-based and role-based selectors (e.g., `page.get_by_text()`, `page.get_by_role()`, `page.locator("h2")`). Tests SHALL NOT require modifications to the production component code. The only exception is Bootstrap's `data-bs-toggle` attribute, which is a framework attribute (not a test hook) and MAY be used for dropdown interaction.

#### Scenario: Verifying the home page heading
- **WHEN** a test navigates to `/`
- **THEN** the test SHALL locate the hero headline using `page.get_by_role("heading", name="Build Frontend in Python", level=1)`

#### Scenario: Verifying a button exists on the FizzBuzz page
- **WHEN** a test navigates to `/sample/fizzbuzz`
- **THEN** the test SHALL locate the "Add" button using `page.get_by_role("button", name="Add")`

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
- **AND** the "Build Frontend in Python" hero heading SHALL be visible

#### Scenario: Navigating from the Home hero to Getting Started
- **WHEN** a test on the home page clicks the "Get Started" button
- **THEN** the URL SHALL change to `/documents/getting-started/what-is-webcompy`
- **AND** the page's heading SHALL be visible
