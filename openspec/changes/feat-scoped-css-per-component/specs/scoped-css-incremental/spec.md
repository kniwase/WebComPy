# Scoped CSS Incremental Management

## Purpose

Scoped component CSS is injected into the page as per-component `<style>` elements identified by `data-webcompy-cid` attributes. This enables idempotent, incremental injection at both browser runtime and during SSG. Unlike the previous monolithic `<style id="webcompy-scoped-styles">` approach, this allows new styles to be added after initial render (e.g., when lazy-loaded components are resolved during SPA navigation) and ensures complete style coverage in SSG output regardless of which page is generated first.

## Requirements

### Requirement: Each component's scoped CSS SHALL be injected as a separate `<style>` element

Each component generator with scoped CSS SHALL produce its own `<style>` element with a `data-webcompy-cid="{hash}"` attribute, where `{hash}` is the component's MD5-based ID.

#### Scenario: Rendering a page with multiple scoped components
- **WHEN** `AppDocumentRoot` renders a page with components Navbar (cid=abc), Home (cid=def), and SyntaxHighlighting (cid=ghi)
- **THEN** the generated HTML SHALL contain:
  - `<style id="webcompy-scoped-styles">*[hidden]{display:none}</style>`
  - `<style data-webcompy-cid="abc">nav[webcompy-cid-abc]{...}</style>`
  - `<style data-webcompy-cid="def">.container[webcompy-cid-def]{...}</style>`
  - `<style data-webcompy-cid="ghi">pre code[webcompy-cid-ghi]{...}</style>`

#### Scenario: Component without scoped_style produces no style element
- **WHEN** a component is registered in `ComponentStore` but has no `scoped_style` set
- **THEN** no `<style data-webcompy-cid="...">` element SHALL be generated for that component

### Requirement: Scoped CSS injection SHALL be idempotent using data-webcompy-cid

The framework SHALL NOT create duplicate `<style>` elements for the same component. Before injecting a style element, it SHALL check for an existing element using `querySelector('style[data-webcompy-cid="{cid}"]')`.

#### Scenario: Browser hydrate on SSG-generated page
- **WHEN** a browser hydrates an SSG-generated page that already contains `<style data-webcompy-cid="abc">` in its HTML
- **THEN** `_reconcile_scoped_styles()` SHALL find the existing element via `querySelector`
- **AND** SHALL NOT create a duplicate

#### Scenario: Multiple calls to _reconcile_scoped_styles
- **WHEN** `_reconcile_scoped_styles()` is called multiple times during a page lifecycle
- **THEN** only the first call SHALL inject styles for newly registered components
- **AND** subsequent calls SHALL detect existing `data-webcompy-cid` elements and skip injection

### Requirement: Scoped CSS SHALL be reconciled on every render

`AppDocumentRoot._render()` SHALL call `_reconcile_scoped_styles()` each render cycle. This function SHALL scan `ComponentStore.components`, check which CIDs are missing from the DOM, and inject only missing `<style>` elements into `<head>`.

#### Scenario: Lazy component resolved during SPA navigation
- **WHEN** a user navigates to a lazy-loaded route for the first time
- **AND** the lazy `ComponentGenerator._resolve()` registers the component into `ComponentStore`
- **THEN** on the next `_render()` call, `_reconcile_scoped_styles()` SHALL detect the new component
- **AND** SHALL inject its `<style data-webcompy-cid="...">` element into `<head>`
- **AND** the component's scoped CSS SHALL apply to its DOM elements

#### Scenario: Multiple lazy components resolved in sequence
- **WHEN** a user navigates through three lazy routes, each resolving a different component with scoped CSS
- **THEN** after each navigation, the newly resolved component's `<style>` element SHALL be injected
- **AND** all three style elements SHALL be present in the DOM

#### Scenario: Server-side render (no DOM)
- **WHEN** `_reconcile_scoped_styles()` is called and `ENVIRONMENT != "pyscript"`
- **THEN** the function SHALL return immediately without performing DOM operations

### Requirement: SSG SHALL pre-resolve all lazy routes before per-route generation

During static site generation, all lazy route entries SHALL be pre-resolved via `_preload()` before the per-route generation loop. This ensures `_register_deferred_components()` registers all component generators into the app's `ComponentStore`, and every generated page includes complete scoped CSS.

#### Scenario: SSG with lazy routes
- **WHEN** `generate_static_site()` is called with a router containing lazy routes
- **THEN** before the per-route generation loop, all `LazyComponentGenerator` entries SHALL be pre-resolved
- **AND** `_register_deferred_components()` SHALL register all component generators into the app's `ComponentStore`
- **AND** every generated HTML page SHALL contain `<style data-webcompy-cid="...">` for all components with scoped CSS, regardless of which route the page represents

### Requirement: AppDocumentRoot SHALL expose scoped_styles as a cid-to-CSS dict

`AppDocumentRoot.scoped_styles` SHALL return a `dict[str, str]` mapping component cid values to their CSS strings, sorted by cid for deterministic ordering. The previously existing `AppDocumentRoot.style` property (concatenated CSS string) SHALL be removed. `WebComPyApp` SHALL forward `scoped_styles` as a property, and the `WebComPyApp.style` forwarding property SHALL be removed.

#### Scenario: Accessing scoped_styles during SSG
- **WHEN** SSG `_html.py` accesses `app.scoped_styles`
- **THEN** it SHALL receive a dict like `{"abc": "nav[webcompy-cid-abc]{...}", "def": ".container[webcompy-cid-def]{...}"}`
- **AND** the keys SHALL be sorted alphabetically
- **AND** components without `scoped_style` SHALL be excluded

### Requirement: The *[hidden] utility rule SHALL remain in a dedicated element

The framework-level `*[hidden]{display:none}` rule SHALL remain in a `<style id="webcompy-scoped-styles">` element, separate from per-component `<style data-webcompy-cid="...">` elements. This rule is not component-specific and SHALL be included in every SSG-generated page.

#### Scenario: Browser runtime with only utility rule
- **WHEN** a `WebComPyApp` runs in browser with no components having scoped CSS
- **THEN** only `<style id="webcompy-scoped-styles">*[hidden]{display:none}</style>` SHALL be present
- **AND** no `data-webcompy-cid` `<style>` elements SHALL exist

#### Scenario: SSG always includes utility rule
- **WHEN** any SSG page is generated
- **THEN** the `<head>` SHALL contain `<style id="webcompy-scoped-styles">*[hidden]{display:none}</style>`
- **AND** per-component `<style data-webcompy-cid="...">` elements SHALL follow it
