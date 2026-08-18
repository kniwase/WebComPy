## MODIFIED Requirements

### Requirement: SSG SHALL pre-resolve all lazy routes before per-route generation

During static site generation, all lazy route entries — including nested layout routes that only appear as parents in the route tree — SHALL be pre-resolved via `_preload()` before the per-route generation loop. Pre-resolution alone SHALL NOT be relied upon for complete style coverage, however: component registration into each render context's component store SHALL be complete regardless of when a component module was first imported (see the registration coverage requirement).

#### Scenario: SSG with lazy routes
- **WHEN** `generate_static_site()` is called with a router containing lazy routes, including nested routes with shared layout components
- **THEN** before the per-route generation loop, all `LazyComponentGenerator` entries in the route tree (including layout/parent routes) SHALL be pre-resolved
- **AND** every generated HTML page SHALL contain `<style data-webcompy-cid="...">` for all components with scoped CSS, regardless of which route the page represents

#### Scenario: Layout-only component styles on every page
- **WHEN** a component (e.g., a sidebar) is imported only by a lazily loaded layout module and is not itself a route component
- **THEN** its `<style data-webcompy-cid="...">` element SHALL appear in every generated page's head, including pages generated after the first one

## ADDED Requirements

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
