# Router — Delta: feat-lazy-routing

## MODIFIED Requirements

### Requirement: The lazy() helper shall defer module import and support shell placeholders
The `lazy()` helper SHALL accept a module path string (e.g., `"pages.docs:DocsPage"`) and return a `LazyComponentGenerator` (subclass of `ComponentGenerator`) that defers `importlib.import_module()` until the route is first matched. The `lazy()` function SHALL also accept an optional `shell` parameter for a loading placeholder component.

`LazyComponentGenerator._resolve()` SHALL perform the actual import and cache the result. `_preload()` SHALL resolve without rendering, enabling speculative loading.

#### Scenario: Defining a lazy route
- **WHEN** a developer writes `Router({"path": "/docs", "component": lazy("pages.docs:DocsPage", __file__)})`
- **THEN** the `pages.docs` module SHALL NOT be imported at startup
- **AND** on first navigation to `/docs`, the module SHALL be imported and `DocsPage` SHALL be rendered

#### Scenario: Lazy route with loading shell
- **WHEN** a developer writes `lazy("pages.docs:DocsPage", __file__, shell=LoadingShell)` and the module is not yet loaded
- **THEN** `LoadingShell` SHALL be rendered while the module is being imported
- **AND** once the module is loaded, the real component SHALL replace the shell

#### Scenario: Preloading a lazy route without rendering
- **WHEN** `_preload()` is called on a `LazyComponentGenerator`
- **THEN** the module SHALL be imported and cached without triggering a render

## ADDED Requirements

### Requirement: RouterLink shall preload lazy routes on hover
`RouterLink` SHALL add a `@mouseenter` event handler that calls `_preload()` on the target `LazyComponentGenerator` when hovered, enabling speculative module import before the user clicks.

#### Scenario: Hovering over a RouterLink with a lazy route
- **WHEN** a user hovers over a `RouterLink` whose target component is a `LazyComponentGenerator`
- **THEN** `_preload()` SHALL be called on the `LazyComponentGenerator`
- **AND** the module SHALL begin importing in the background
- **AND** navigation to that route SHALL use the cached import if it has completed