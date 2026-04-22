# CLI — Delta: feat-hydration-partial

## ADDED Requirements

### Requirement: Loading screen overlay shall be semi-transparent during hydration
The generated loading screen overlay (`#webcompy-loading`) SHALL use a semi-transparent dark background (e.g., `rgba(0, 0, 0, 0.5)`) instead of an opaque background. This allows pre-rendered content to be visible during the hydration phase, giving the user an immediate visual indication that content is loading.

#### Scenario: Generated HTML includes semi-transparent loading screen
- **WHEN** the CLI generates an `index.html` with a loading screen
- **THEN** the `#webcompy-loading` overlay SHALL use a semi-transparent dark background
- **AND** pre-rendered content SHALL remain visible beneath the overlay during hydration