## MODIFIED Requirements

### Requirement: Demo iframes SHALL display a loading screen during Pyodide initialization
Each demo iframe SHALL display a loading screen overlay immediately when the iframe loads, before Pyodide initializes. The demo loading screen SHALL visually match the framework's refined default `overlay` presentation (compact spinner on a lightly translucent backdrop) while keeping the `#webcompy-loading` element contract. The loading screen SHALL be automatically removed by the framework when `AppDocumentRoot._render()` completes its first render.

#### Scenario: Loading screen appears before Pyodide starts
- **WHEN** an iframe loads `standard.html`
- **THEN** a `<div id="webcompy-loading">` SHALL be present in the static HTML
- **AND** the loading overlay SHALL be visible immediately without waiting for JavaScript

#### Scenario: Loading screen is removed after demo renders
- **WHEN** the demo's `WebComPyApp` completes `app.run()`
- **THEN** the framework's `_render()` method SHALL remove `#webcompy-loading` from the DOM
- **AND** the demo app content SHALL become visible
