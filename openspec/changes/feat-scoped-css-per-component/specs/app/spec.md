## MODIFIED Requirements

### Requirement: The application shall support scoped CSS injection

All registered components' scoped CSS SHALL be collected and injected into the document as per-component `<style>` elements identified by `data-webcompy-cid` attributes. Each app SHALL have its own `ComponentStore` in its DI scope, ensuring style collection is isolated per app. A single `<style id="webcompy-scoped-styles">` element SHALL contain the framework-level `*[hidden]{display:none}` utility rule, separate from per-component style elements.

#### Scenario: Rendering multiple components with scoped styles
- **WHEN** components `A` and `B` each define scoped CSS
- **THEN** each component's CSS SHALL appear in its own `<style data-webcompy-cid="...">` element in the document head
- **AND** the `*[hidden]{display:none}` utility rule SHALL appear in `<style id="webcompy-scoped-styles">`
- **AND** each style SHALL only affect elements within its respective component

#### Scenario: Lazy component resolved after initial render
- **WHEN** a lazy-loaded component with scoped CSS is resolved during SPA navigation
- **THEN** its `<style data-webcompy-cid="...">` element SHALL be injected into `<head>` on the next render cycle
- **AND** no duplicate style elements SHALL be created