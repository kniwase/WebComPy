## MODIFIED Requirements

### Requirement: Reactive styles shall be renderable during SSR

During static site generation and prerendered serving, the framework SHALL evaluate each registered reactive style once and emit the resulting CSS as a `<style data-webcompy-cid-rx>` element in the generated HTML. The SSR output SHALL reflect the signal values at the time of generation. Collection of reactive styles for the head SHALL run after the component tree render completes and pending render-settling async work has been awaited, so reactive styles registered during async component setup SHALL also be emitted.

#### Scenario: SSG renders initial reactive style
- **WHEN** a component with a reactive style is included in a static-generated page
- **THEN** the generated HTML SHALL contain a `<style data-webcompy-cid-rx>` element
- **AND** its `textContent` SHALL equal the value of the reactive style's `Computed` at generation time

#### Scenario: Reactive style registered during async setup
- **WHEN** a component with async setup registers a reactive scoped style
- **AND** the page containing the component is prerendered
- **THEN** the generated HTML SHALL contain the corresponding `<style data-webcompy-cid-rx>` element after the async work settles
