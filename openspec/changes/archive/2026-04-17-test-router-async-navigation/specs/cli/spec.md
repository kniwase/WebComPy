## ADDED Requirements

### Requirement: E2E tests shall verify async on_after_rendering works during router navigation
The e2e test suite SHALL include test cases that verify components with async operations in `on_after_rendering` work correctly when navigated to via RouterLink (reactive path) and direct URL (hydration path).

#### Scenario: Navigating to async page via RouterLink
- **WHEN** a user navigates to a page that performs async operations in `on_after_rendering` by clicking a RouterLink
- **THEN** the page SHALL render without errors
- **AND** the async data SHALL be fetched and displayed

#### Scenario: Direct URL access to async page
- **WHEN** a user accesses a page with async `on_after_rendering` directly via URL
- **THEN** the page SHALL render without errors
- **AND** the async data SHALL be fetched and displayed