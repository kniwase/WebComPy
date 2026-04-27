# Router

## Purpose

A front-end router solves a fundamental problem in single-page applications: synchronizing the browser's URL with the application's visible content. Without routing, navigating between "pages" requires a full page reload. With routing, only the relevant portion of the DOM changes while the browser URL updates, enabling a seamless user experience.

WebComPy provides two routing modes — hash mode for simple deployments (like static hosting services) and history mode for clean URLs (requiring server-side support). The router integrates with the reactive system so that URL changes automatically propagate to the UI: when a route changes, the page component updates without any manual wiring.

**What WebComPy does not yet provide:** Other frameworks support nested routes and route guards (before/after navigation hooks). The `Location` object's `popstate` proxy requires manual `destroy()` calls for cleanup.

## Requirements

### Requirement: The router shall synchronize the browser URL with displayed content
When the URL changes — whether through user navigation (clicking links, using browser back/forward) or programmatic navigation — the router SHALL determine which page component to display and render it.

#### Scenario: Clicking a navigation link
- **WHEN** a user clicks a `RouterLink`
- **THEN** the browser URL SHALL update without a full page reload
- **AND** the page component matching the new URL SHALL replace the currently displayed page

#### Scenario: Using browser back/forward buttons
- **WHEN** a user presses the browser back button
- **THEN** the router SHALL detect the URL change via `popstate`
- **AND** the previously displayed page component SHALL be restored

### Requirement: The router shall support hash-based and history-based routing
Hash mode SHALL use `#/path` URLs that work without server configuration. History mode SHALL use clean `/path` URLs that require server-side routing support.

#### Scenario: Deploying with hash mode
- **WHEN** an app is configured with `Router(mode="hash")`
- **THEN** all `RouterLink` URLs SHALL use the `#/path` format
- **AND** the app SHALL work on any static hosting service without server configuration

#### Scenario: Deploying with history mode
- **WHEN** an app is configured with `Router(mode="history")`
- **THEN** `RouterLink` URLs SHALL use clean `/path` format
- **AND** the server SHALL be configured to redirect all routes to the app's entry point

### Requirement: Route definitions shall support path parameters
Developers SHALL be able to define routes with dynamic segments (e.g., `/users/{id}`) that capture values from the URL and pass them to page components.

#### Scenario: Navigating to a user profile
- **WHEN** a route is defined as `/users/{id}` and the URL is `/users/42`
- **THEN** the page component SHALL receive `path_params={"id": "42"}` in its router context
- **AND** `RouterLink(to="/users/{id}", path_params=id_reactive)` SHALL generate `/users/42`

### Requirement: Route context shall provide URL information to page components
Each page component SHALL receive a router context containing the current path, path parameters, query parameters, and navigation state.

#### Scenario: Accessing route information in a component
- **WHEN** a user navigates to `/search?q=python&page=2`
- **THEN** the page component SHALL receive `context.props.path` as the full path
- **AND** `context.props.query` as `{"q": "python", "page": "2"}`
- **AND** `context.props.path_params` as any path parameters

### Requirement: Navigation shall support passing state between pages
When navigating via `RouterLink`, developers SHALL be able to pass state data that persists across navigation events (accessible via `history.state`).

#### Scenario: Passing data between pages
- **WHEN** a `RouterLink` includes `params` with JSON-serializable data
- **THEN** that data SHALL be stored in `history.state`
- **AND** the destination page SHALL be able to access it via `context.props.params`

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

### Requirement: RouterLink shall preload lazy routes on hover
`RouterLink` SHALL add a `mouseenter` event handler (via the `events` parameter, which uses `addEventListener`) that preloads the target route's `LazyComponentGenerator` when hovered. `Router` SHALL provide a `_get_component_for_path()` method that returns the `ComponentGenerator` for a given path.

#### Scenario: Hovering over a RouterLink with a lazy route
- **WHEN** a user hovers over a `RouterLink` whose target component is a `LazyComponentGenerator`
- **THEN** `_preload()` SHALL be called on the `LazyComponentGenerator`
- **AND** the module SHALL begin importing in the background
- **AND** navigation to that route SHALL use the cached import if it has completed

#### Scenario: Hovering over a RouterLink with an eager route
- **WHEN** a user hovers over a `RouterLink` whose target component is a regular `ComponentGenerator`
- **THEN** no additional action SHALL be taken

### Requirement: RouterView shall be a DynamicElement (not an Element)
`RouterView` SHALL extend `DynamicElement` instead of `Element`. This removes the unnecessary `<div webcompy-routerview>` wrapper from the DOM and provides the `_on_set_parent()` lifecycle hook for scheduling auto-preload. The `webcompy-routerview` attribute SHALL be removed as it has no consumers.

#### Scenario: RouterView does not produce a DOM node
- **WHEN** a `RouterView` is rendered in the browser
- **THEN** it SHALL NOT create a `<div>` element
- **AND** the `SwitchElement` child SHALL be positioned directly in the parent node
- **AND** `RouterView._on_set_parent()` SHALL initialize children and schedule lazy route preloading

#### Scenario: RouterView SSG output
- **WHEN** `generate_html()` produces output containing a `RouterView`
- **THEN** the output SHALL NOT contain a `<div webcompy-routerview>` wrapper
- **AND** the route content SHALL be rendered directly without an extra `<div>`

### Requirement: A default page shall be shown when no route matches
When the current URL does not match any defined route, the router SHALL render a default component or display "Not Found".

#### Scenario: Navigating to an undefined route
- **WHEN** the URL matches no defined route and no default component is provided
- **THEN** the text "Not Found" SHALL be displayed

#### Scenario: Navigating to an undefined route with a default component
- **WHEN** the URL matches no defined route and a default component is provided
- **THEN** the default component SHALL be rendered with the current path and query information

### Requirement: ComponentGenerator private attributes shall use single-underscore naming
`ComponentGenerator` SHALL use single-underscore private attributes (`_name`, `_id`, `_style`, `_registered`, `_component_def`) instead of name-mangled attributes (`__name`, `__id`, etc.). `ComponentStore` SHALL use `_components` instead of `__components`. This enables `LazyComponentGenerator` (a subclass) to access and delegate to these attributes properly. This is a behavior-preserving refactor with no public API change.

#### Scenario: Subclass accessing ComponentGenerator attributes
- **WHEN** `LazyComponentGenerator` subclasses `ComponentGenerator`
- **THEN** it SHALL be able to read and write `_name`, `_id`, `_style`, `_registered`, `_component_def` on the parent class