# CLI — Delta: fix-prerender-hidden-attribute

## MODIFIED Requirements

### Requirement: Prerendered HTML shall include visible app content
When the CLI generates HTML with prerendering, the `#webcompy-app` element SHALL NOT include a `hidden` attribute so that the pre-rendered content is visible beneath the loading screen overlay during hydration.

#### Scenario: Prerendered HTML has no hidden attribute on app root
- **WHEN** a developer runs `python -m webcompy generate` for an app with prerendering enabled
- **THEN** the generated `#webcompy-app` div SHALL NOT have a `hidden` attribute
- **AND** the pre-rendered content SHALL be visible to the user through the semi-transparent loading overlay