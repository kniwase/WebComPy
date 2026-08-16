## MODIFIED Requirements

### Requirement: The loading indicator shall be removed on first render
When the application finishes its first render, the `#webcompy-loading` element SHALL be removed from the DOM, revealing the fully rendered application. Removal SHALL follow the transition sequence defined by the `loading-screen` capability: the element SHALL fade out over the configured duration before removal, the mount element's `aria-busy` attribute SHALL be cleared, and any dormant content treatment SHALL be ended with a wake-up transition. Browser-side removal mechanics SHALL be driven by `data-wc-*` attributes on the loading element, falling back to framework defaults when the attributes are absent (e.g., library usage without CLI-generated HTML).

#### Scenario: Initial page load with app.run()
- **WHEN** a user opens a WebComPy app and `app.run()` is called
- **THEN** loading chrome SHALL be subject to the grace period while PyScript initializes
- **AND** once the app renders, the loading element SHALL fade out and be removed

#### Scenario: Removal honors loading element attributes
- **WHEN** the generated `#webcompy-loading` element carries a custom fade duration attribute
- **THEN** the removal sequence SHALL use that duration instead of the framework default

#### Scenario: Library usage without generated HTML
- **WHEN** `app.run()` completes in a page that has no `#webcompy-loading` element
- **THEN** no error SHALL occur and the application SHALL render normally
