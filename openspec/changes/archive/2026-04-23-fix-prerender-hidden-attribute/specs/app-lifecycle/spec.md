# App Lifecycle — Delta: fix-prerender-hidden-attribute

## MODIFIED Requirements

### Requirement: Prerendered app root shall be visible on page load
When the CLI generates HTML with prerendering enabled, the `#webcompy-app` div SHALL NOT include a `hidden` attribute. The pre-rendered content SHALL be immediately visible in the browser, with the semi-transparent loading overlay allowing the user to see content beneath it during hydration.

#### Scenario: Inspecting prerendered HTML output
- **WHEN** the CLI generates HTML with `prerender=True`
- **THEN** the `#webcompy-app` div SHALL NOT have a `hidden` attribute
- **AND** the pre-rendered content SHALL be visible beneath the semi-transparent loading overlay

#### Scenario: Non-prerendered HTML output
- **WHEN** the CLI generates HTML with `prerender=False`
- **THEN** the `#webcompy-app` div SHALL have a `hidden` attribute
- **AND** the content SHALL remain invisible until PyScript initializes and removes `hidden`