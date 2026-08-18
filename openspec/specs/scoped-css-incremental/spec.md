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

`AppDocumentRoot._render()` SHALL call `HeadElement._render()` each render cycle. `HeadElement._render()` SHALL scan `ComponentStore.components` via DI injection, check which CIDs are missing from the DOM, and inject only missing `<style>` elements into `<head>`.

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

During static site generation, all lazy route entries — including nested layout routes that only appear as parents in the route tree — SHALL be pre-resolved via `_preload()` before the per-route generation loop. Pre-resolution alone SHALL NOT be relied upon for complete style coverage, however: component registration into each render context's component store SHALL be complete regardless of when a component module was first imported (see the registration coverage requirement).

#### Scenario: SSG with lazy routes
- **WHEN** `generate_static_site()` is called with a router containing lazy routes, including nested routes with shared layout components
- **THEN** before the per-route generation loop, all `LazyComponentGenerator` entries in the route tree (including layout/parent routes) SHALL be pre-resolved
- **AND** every generated HTML page SHALL contain `<style data-webcompy-cid="...">` for all components with scoped CSS, regardless of which route the page represents

#### Scenario: Layout-only component styles on every page
- **WHEN** a component (e.g., a sidebar) is imported only by a lazily loaded layout module and is not itself a route component
- **THEN** its `<style data-webcompy-cid="...">` element SHALL appear in every generated page's head, including pages generated after the first one

### Requirement: Every component generator SHALL be registered in every render context's component store

Component registration coverage SHALL NOT depend on whether a component module was first imported with or without an active DI scope. Every `ComponentGenerator` created in the process SHALL be re-registered into each new render context's `ComponentStore` (subject to the existing per-store deduplication and cross-app exclusion rules), so scoped-style coverage is uniform across all render contexts.

#### Scenario: Component first imported during an earlier request
- **WHEN** a component module is first imported while render context A is active (registering its generator into A's store only)
- **AND** a later render context B is created for the same app
- **THEN** the generator SHALL also be present in B's component store
- **AND** B's emitted scoped styles SHALL include that component's CSS

#### Scenario: Dev server serves lazy page styles on every request
- **WHEN** the dev or prod server handles a request for a route whose component module has been imported at any earlier point in the process
- **THEN** the response HTML SHALL contain that component's `<style data-webcompy-cid="...">` element, on the first request and on every subsequent request

### Requirement: Scoped style collection for prerendered HTML SHALL run after rendering completes

When generating prerendered HTML (SSG, prod server, dev server), the collection of static and reactive scoped styles for the `<head>` SHALL run only after the component tree render has completed and pending render-settling async work has been awaited. Components registered during the render itself, and reactive styles created during (possibly async) component setup, SHALL be included in the emitted head.

#### Scenario: Component registered during the current render
- **WHEN** a component generator is first registered into the current context's store while the page is rendering (e.g., via lazy resolution mid-render)
- **THEN** its scoped style SHALL still appear in the generated page's head

#### Scenario: Reactive style created during async setup
- **WHEN** a component with async setup registers a reactive scoped style
- **THEN** the generated HTML SHALL contain its `<style data-webcompy-cid-rx="...">` element reflecting the settled value

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

### Requirement: Scoped CSS output SHALL be verifiable via create_test_asgi_app

The `create_test_asgi_app()` test utility SHALL produce HTML output that includes per-component `<style data-webcompy-cid="...">` elements for components with scoped CSS. Tests using `httpx` against the test ASGI app SHALL be able to verify scoped CSS element presence in SSR output.

#### Scenario: SSR integration test verifies scoped CSS elements
- **WHEN** a test creates a `WebComPyApp` with a page component that has scoped CSS
- **AND** creates an ASGI app via `create_test_asgi_app(app)`
- **AND** sends a GET request via httpx to the app
- **THEN** the response body SHALL contain `data-webcompy-cid="` attribute string
- **AND** the response body SHALL contain `*[hidden]{display: none;}`

### Requirement: Incrementally injected static scoped CSS shall support `:host`

When a named component's static scoped style contains `:host` or `:host(<compound-selector>)`, the incrementally injected `<style data-webcompy-cid>` content SHALL replace the host pseudo-class with the component's custom-element selector and retain the normal cid attribute scoping. The same transformed CSS SHALL be used for browser runtime injection and SSR/SSG output.

#### Scenario: Injecting a host rule at browser runtime
- **WHEN** a named component with scoped style `{":host": {"display": "block"}}` is registered during browser runtime
- **THEN** its per-component style element SHALL contain a selector for the named custom-element wrapper
- **AND** the selector SHALL include the component cid attribute

#### Scenario: Rendering a host rule during SSG
- **WHEN** SSG emits a named component's scoped style containing `:host(.active)`
- **THEN** the generated per-component style element SHALL contain the equivalent named-element class selector
- **AND** the output SHALL remain wrapped in `@layer webcompy-scope`

#### Scenario: Reconciling a newly resolved host style
- **WHEN** a lazy named component with a `:host` scoped style is resolved after the initial render
- **THEN** the next scoped-style reconciliation SHALL inject exactly one matching style element
- **AND** the generated rule SHALL use the same selector as the initial SSR or runtime path

### Requirement: Incremental scoped CSS shall retain cid-based component isolation

Adding `:host` support SHALL not replace cid-attribute scoping. Existing selectors and nested component boundaries SHALL continue to use `webcompy-cid-*` attributes, and a named-element tag selector SHALL not be used as a general replacement for cid scoping.

#### Scenario: Existing descendant selector remains cid-scoped
- **WHEN** a named component contains both `:host` and `.button` scoped rules
- **THEN** the host rule SHALL target the wrapper
- **AND** the `.button` rule SHALL retain the existing cid-scoped descendant behavior

#### Scenario: Nested component styles remain isolated
- **WHEN** a named component contains a nested component with an element sharing a class name
- **THEN** the parent component's descendant rule SHALL not leak into the nested component's owned subtree
- **AND** the nested component's own scoped style SHALL remain independent
