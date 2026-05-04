## MODIFIED Requirements

### Requirement: The router shall auto-preload lazy routes after initial render
When `Router` is created with `preload=True` (the default), the router SHALL automatically preload (resolve) all unresolved lazy routes after the initial page render completes. In the browser, preloading SHALL be scheduled after the initial render's loading screen is removed, using `setTimeout(0)` to avoid blocking. In non-browser (SSG) environments, preloading SHALL happen immediately during `RouterView._on_set_parent()`.

#### Scenario: Auto-preloading lazy routes in the browser
- **WHEN** a developer creates `Router({"path": "/", "component": HomePage}, {"path": "/docs", "component": lazy("myapp.pages.docs:DocsPage", __file__)}, preload=True)`
- **THEN** after the home page renders and the loading screen is removed, `setTimeout(0)` SHALL be used to import the `myapp.pages.docs` module
- **AND** subsequent navigation to `/docs` SHALL be instant (module already loaded)

#### Scenario: Auto-preloading disabled
- **WHEN** a developer creates `Router(..., preload=False)`
- **THEN** lazy routes SHALL NOT be auto-preloaded after the initial render
- **AND** lazy routes SHALL only be imported on first navigation

#### Scenario: Auto-preloading in SSG
- **WHEN** `Router.preload_lazy_routes()` is called in a non-browser environment
- **THEN** all unresolved lazy routes SHALL be resolved immediately (no `setTimeout`)
- **AND** all page components SHALL be available for SSG rendering

#### Scenario: A lazy route fails to preload
- **WHEN** preloading a `LazyComponentGenerator` fails (e.g., `ModuleNotFoundError`)
- **THEN** the application SHALL NOT crash
- **AND** the `LazyComponentGenerator._resolve_error` flag SHALL be set to `True`
- **AND** subsequent navigation to that route SHALL attempt resolution again via `_resolve()`

### Requirement: RouterView shall be a DynamicElement (not an Element)
`RouterView` SHALL extend `DynamicElement` instead of `Element`. This removes the unnecessary `<div webcompy-routerview>` wrapper from the DOM and provides the `_on_set_parent()` lifecycle hook. In non-browser environments, `_on_set_parent()` SHALL schedule auto-preload. In browser environments, auto-preload SHALL be deferred to `AppDocumentRoot._render()` after the loading screen is removed.

#### Scenario: RouterView does not produce a DOM node
- **WHEN** a `RouterView` is rendered in the browser
- **THEN** it SHALL NOT create a `<div>` element
- **AND** the `SwitchElement` child SHALL be positioned directly in the parent node
- **AND** `RouterView._on_set_parent()` SHALL initialize children and, in non-browser environments, schedule lazy route preloading

#### Scenario: RouterView SSG output
- **WHEN** `generate_html()` produces output containing a `RouterView`
- **THEN** the output SHALL NOT contain a `<div webcompy-routerview>` wrapper
- **AND** the route content SHALL be rendered directly without an extra `<div>`
