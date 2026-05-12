# Reactive Dropdown

## Purpose

Demonstrate that WebComPy's reactive system (`Signal`, `Computed`, event handlers) is sufficient to implement common UI interactions like dropdown menus without relying on external JavaScript libraries. This pattern serves as a foundation for future UI component libraries.

## Requirements

### Requirement: Dropdown state SHALL be managed by reactive Signals

Each dropdown menu SHALL use a `Signal[bool]` to track its open/closed state. Clicking the toggle button SHALL invert the Signal value.

#### Scenario: Clicking a dropdown toggle
- **WHEN** a user clicks a dropdown toggle button
- **THEN** the dropdown menu SHALL open (if closed) or close (if open)
- **AND** this SHALL be reflected in the `aria-expanded` attribute

### Requirement: Dropdown menus SHALL close when clicking outside

Clicking anywhere outside an open dropdown menu SHALL close all open dropdowns.

#### Scenario: Clicking outside an open dropdown
- **WHEN** a dropdown menu is open
- **AND** the user clicks outside the dropdown menu and toggle button
- **THEN** the dropdown SHALL close
- **AND** the `aria-expanded` attribute SHALL update to `"false"`

### Requirement: Dropdown menus SHALL support multiple instances with exclusive display

Multiple dropdown menus SHALL be able to coexist, each with independent open/close state. By default, opening one dropdown SHALL close all other dropdowns (exclusive display) to prevent UI clutter. All dropdowns SHALL close when clicking outside.

#### Scenario: Multiple dropdowns on the same page with exclusive display
- **WHEN** a navbar contains two dropdown menus
- **AND** the first dropdown is opened
- **THEN** clicking the second dropdown toggle SHALL open the second menu
- **AND** the first menu SHALL close (exclusive display)

#### Scenario: Clicking outside closes all dropdowns
- **WHEN** multiple dropdowns are open
- **AND** the user clicks outside any dropdown menu and toggle button
- **THEN** all dropdowns SHALL close
- **AND** all `aria-expanded` attributes SHALL update to `"false"`

### Requirement: Dropdowns SHALL maintain proper ARIA attributes

Each dropdown toggle SHALL have:
- `aria-expanded` reflecting the current open state
- `aria-haspopup="true"`
- `aria-controls` referencing the menu element id

#### Scenario: Screen reader navigation
- **WHEN** a dropdown is closed
- **THEN** `aria-expanded` SHALL be `"false"`
- **WHEN** the dropdown is opened
- **THEN** `aria-expanded` SHALL be `"true"`

### Requirement: Navigation links SHALL remain functional

All `RouterLink` components within dropdown menus SHALL continue to work correctly for SPA navigation.

#### Scenario: Clicking a dropdown navigation link
- **WHEN** a user clicks a link inside an open dropdown menu
- **THEN** navigation SHALL occur via the router
- **AND** the dropdown SHALL close
