## MODIFIED Requirements

### Requirement: Scoped CSS SHALL be injected at browser runtime when SSR is absent

The framework SHALL inject scoped component styles as per-component `<style data-webcompy-cid="{hash}">` elements in `document.head`, along with a single `<style id="webcompy-scoped-styles">` element for the framework-level `*[hidden]{display:none}` rule. Style injection SHALL be idempotent: before creating any `<style>` element, the framework SHALL check for an existing element with the same identifier (`data-webcompy-cid` or `id`). When SSR has already produced these elements, the runtime SHALL detect them and skip injection. New components registered after initial render (e.g., lazy-loaded routes) SHALL have their styles injected on the next render cycle.

#### Scenario: Runtime injection when SSR is absent
- **WHEN** a `WebComPyApp` is created and `app.run()` is called at browser runtime with no pre-existing `<style id="webcompy-scoped-styles">` or `<style data-webcompy-cid="...">` elements in the DOM
- **THEN** `AppDocumentRoot._render()` SHALL create a `<style id="webcompy-scoped-styles">` element with `*[hidden]{display:none}`
- **AND** SHALL create a `<style data-webcompy-cid="...">` element for each registered component that has `scoped_style`
- **AND** SHALL append all style elements to `document.head`
- **AND** component `scoped_style` rules SHALL apply correctly

#### Scenario: No duplicate when SSR has already injected styles
- **WHEN** a `WebComPyApp` hydrates a page that was server-side rendered
- **AND** the SSR output already contains both `<style id="webcompy-scoped-styles">` and `<style data-webcompy-cid="...">` elements in the document head
- **THEN** `_reconcile_scoped_styles()` SHALL check for existing elements via `querySelector`
- **AND** finding existing elements, SHALL skip injection for each
- **AND** no duplicate `<style>` elements SHALL be created

#### Scenario: Runtime style injection in isolated contexts
- **WHEN** a `WebComPyApp` runs inside an iframe with no SSR
- **THEN** scoped component styles SHALL be injected at runtime as per-component `<style>` elements
- **AND** components inside the iframe SHALL render with their defined `scoped_style` CSS

#### Scenario: Lazy component styles injected after initial render
- **WHEN** a `WebComPyApp` is already rendered in the browser
- **AND** a lazy route component with `scoped_style` is resolved for the first time
- **THEN** on the next render cycle, `_reconcile_scoped_styles()` SHALL detect the new component
- **AND** SHALL inject a `<style data-webcompy-cid="...">` element for it
- **AND** SHALL NOT duplicate styles for previously injected components

### Requirement: AppDocumentRoot SHALL expose scoped_styles as a cid-to-CSS dict

`AppDocumentRoot.style` (concatenated CSS string) SHALL be removed. `AppDocumentRoot.scoped_styles` SHALL return a `dict[str, str]` mapping component cid values to their full CSS strings, sorted by cid for deterministic ordering. Components without `scoped_style` SHALL be excluded.

#### Scenario: Accessing scoped_styles from AppDocumentRoot
- **WHEN** `AppDocumentRoot.scoped_styles` is accessed
- **THEN** it SHALL iterate `ComponentStore.components` and return `{cid: css_string}` for each component with non-empty `scoped_style`
- **AND** the dict keys SHALL be sorted alphabetically
