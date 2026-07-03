## ADDED Requirements

### Requirement: Navbar dropdown does not overflow viewport on desktop

The navbar dropdown menu SHALL be positioned so that it remains fully within the viewport when opened on desktop screens (width > 768px). The dropdown SHALL NOT extend beyond the right edge of the viewport.

#### Scenario: Demos dropdown opens within viewport on 1440px screen

- **WHEN** the user clicks the "Demos" dropdown toggle on a 1440px-wide viewport
- **THEN** the entire dropdown menu renders within the viewport bounds without horizontal overflow

#### Scenario: Demos dropdown opens within viewport on 1024px screen

- **WHEN** the user clicks the "Demos" dropdown toggle on a 1024px-wide viewport
- **THEN** the entire dropdown menu renders within the viewport bounds without horizontal overflow

#### Scenario: Dropdown content is fully readable

- **WHEN** the dropdown is open
- **THEN** all text content including the longest menu item ("Matplotlib Sample") is fully visible without horizontal scrolling or clipping
