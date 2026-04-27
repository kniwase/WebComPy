# Router — Delta: feat-lazy-routing

## MODIFIED Requirements

### Requirement: The router shall support lazy-loaded route components
Developers SHALL be able to define routes that defer module import until the route is first matched, reducing initial startup time. A `lazy()` helper SHALL accept an absolute module path string (e.g., `"myapp.pages.docs:DocsPage"`) and a `caller_file` parameter, returning a `LazyComponentGenerator` (subclass of `ComponentGenerator`) that defers `importlib.import_module()` until first use.

`LazyComponentGenerator._resolve()` SHALL perform the actual import and cache the result. `_preload()` SHALL resolve without rendering, enabling speculative loading.

The `import_path` parameter in `lazy()` SHALL use an absolute dotted module path. Relative paths (starting with `.`) SHALL NOT be supported.

`lazy()` SHALL validate the `import_path` format at call time, raising `WebComPyRouterException` if the format is invalid (missing `:` separator, empty module path, or empty attribute name). Module existence and attribute type validation SHALL occur at `_resolve()` time (when the module is actually imported).

#### Scenario: Defining a lazy route
- **WHEN** a developer writes `Router({"path": "/docs", "component": lazy("myapp.pages.docs:DocsPage", __file__)})`
- **THEN** the `myapp.pages.docs` module SHALL NOT be imported at startup
- **AND** on first navigation to `/docs`, the module SHALL be imported and `DocsPage` SHALL be rendered

#### Scenario: Invalid import_path format
- **WHEN** a developer writes `lazy("DocsPage", __file__)` (missing module path)
- **THEN** `WebComPyRouterException` SHALL be raised at call time with a descriptive error message

#### Scenario: Lazy route resolves to non-ComponentGenerator
- **WHEN** `lazy("myapp.pages.docs:some_function", __file__)` resolves to a non-`ComponentGenerator` attribute
- **THEN** `WebComPyRouterException` SHALL be raised at resolution time indicating the attribute is not a `ComponentGenerator`

#### Scenario: Preloading a lazy route without rendering
- **WHEN** `_preload()` is called on a `LazyComponentGenerator`
- **THEN** the module SHALL be imported and cached without triggering a render

### Requirement: The router shall auto-preload lazy routes after initial render
When `Router` is created with `preload=True` (the default), the router SHALL automatically preload (resolve) all unresolved lazy routes after the initial page render. In the browser, preloading SHALL be scheduled via `setTimeout(0)` to avoid blocking the initial render. In non-browser (SSG) environments, preloading SHALL happen immediately.

#### Scenario: Auto-preloading lazy routes in the browser
- **WHEN** a developer creates `Router({"path": "/", "component": HomePage}, {"path": "/docs", "component": lazy("myapp.pages.docs:DocsPage", __file__)}, preload=True)`
- **THEN** after the home page renders, `setTimeout(0)` SHALL be used to import the `myapp.pages.docs` module
- **AND** subsequent navigation to `/docs` SHALL be instant (module already loaded)

#### Scenario: Auto-preloading disabled
- **WHEN** a developer creates `Router(..., preload=False)`
- **THEN** lazy routes SHALL NOT be auto-preloaded after the initial render
- **AND** lazy routes SHALL only be imported on first navigation

#### Scenario: Auto-preloading in SSG
- **WHEN** `Router.preload_lazy_routes()` is called in a non-browser environment
- **THEN** all unresolved lazy routes SHALL be resolved immediately (no `setTimeout`)
- **AND** all page components SHALL be available for SSG rendering

## ADDED Requirements

### Requirement: RouterLink shall preload lazy routes on hover
`RouterLink` SHALL add a `mouseenter` event handler that preloads the target route's `LazyComponentGenerator` when hovered, enabling speculative module import before the user clicks. `Router` SHALL provide a `_get_component_for_path()` method that returns the `ComponentGenerator` for a given path for use by `RouterLink`.

#### Scenario: Hovering over a RouterLink with a lazy route
- **WHEN** a user hovers over a `RouterLink` whose target component is a `LazyComponentGenerator`
- **THEN** `_preload()` SHALL be called on the `LazyComponentGenerator`
- **AND** the module SHALL begin importing in the background
- **AND** navigation to that route SHALL use the cached import if it has completed

#### Scenario: Hovering over a RouterLink with an eager route
- **WHEN** a user hovers over a `RouterLink` whose target component is a regular `ComponentGenerator`
- **THEN** no additional action SHALL be taken

### Requirement: ComponentGenerator private attributes shall use single-underscore naming
`ComponentGenerator` SHALL use single-underscore private attributes (`_name`, `_id`, `_style`, `_registered`, `_component_def`) instead of name-mangled attributes (`__name`, `__id`, etc.). `ComponentStore` SHALL use `_components` instead of `__components`. This enables `LazyComponentGenerator` (a subclass) to access and delegate to these attributes properly. This is a behavior-preserving refactor with no public API change.

#### Scenario: Subclass accessing ComponentGenerator attributes
- **WHEN** `LazyComponentGenerator` subclasses `ComponentGenerator`
- **THEN** it SHALL be able to read and write `_name`, `_id`, `_style`, `_registered`, `_component_def` on the parent class