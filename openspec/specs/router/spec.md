# Router

## Purpose

A front-end router solves a fundamental problem in single-page applications: synchronizing the browser's URL with the application's visible content. Without routing, navigating between "pages" requires a full page reload. With routing, only the relevant portion of the DOM changes while the browser URL updates, enabling a seamless user experience.

WebComPy provides two routing modes — hash mode for simple deployments (like static hosting services) and history mode for clean URLs (requiring server-side support). The router integrates with the reactive system so that URL changes automatically propagate to the UI: when a route changes, the page component updates without any manual wiring.

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

### Requirement: RouterPage shall support nested children
`RouterPage` SHALL accept an optional `children: list[RouterPage]` (recursive). Child paths SHALL be joined under the parent path (`/docs` + `/guide` → `/docs/guide`). A child with path `""` SHALL be the index route, rendered when the parent path matches exactly. A parent page that has `children` SHALL NOT be rendered as a leaf itself; a bare parent-path request with no index child SHALL fall through to the router-level default. Flat page definitions (no `children`) SHALL behave exactly as before.

#### Scenario: Joined paths
- **WHEN** a page `{path: "/docs", component: DocsLayout, children: [{path: "/guide", component: GuidePage}]}` is defined and the URL is `/docs/guide`
- **THEN** the match chain SHALL be `[DocsLayout, GuidePage]`

#### Scenario: Index route
- **WHEN** `/docs` has an index child `{path: "", component: DocsIndex}` and the URL is `/docs`
- **THEN** the match chain SHALL be `[DocsLayout, DocsIndex]`

#### Scenario: Bare parent without index falls to default
- **WHEN** `/docs` has children but no `""` index child and the URL is exactly `/docs`
- **THEN** the router-level default SHALL be rendered

#### Scenario: Flat routes unchanged
- **WHEN** pages are defined without `children`
- **THEN** matching, rendering, and context SHALL behave exactly as single-level chains

### Requirement: Route context shall provide URL information to page components
Each page component SHALL receive a router context containing the current path, path parameters, query parameters, and navigation state.

#### Scenario: Accessing route information in a component
- **WHEN** a user navigates to `/search?q=python&page=2`
- **THEN** the page component SHALL receive `context.props.path` as the full path
- **AND** `context.props.query` as `{"q": "python", "page": "2"}`
- **AND** `context.props.path_params` as any path parameters

### Requirement: RouterContext path_params shall accumulate ancestor params
The `RouterContext` passed to a level-N component SHALL contain `path_params` merged from levels 0 through N (child wins on name collision). `path` SHALL be the full current path; `query` and `params` (state) SHALL be navigation-level values shared by all levels.

#### Scenario: Child sees ancestor param
- **WHEN** the URL is `/users/42/docs/7` matching `/users/{uid}` → `/docs/{doc_id}`
- **THEN** the leaf component's `context.props.path_params` SHALL contain both `uid` (`"42"`) and `doc_id` (`"7"`)

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
When `Router` is created with `preload=True` (the default), the router SHALL automatically preload (resolve) all unresolved lazy routes that have not previously failed after the initial page render completes. In the browser, preloading SHALL be scheduled after the initial render's loading screen is removed, using `setTimeout(0)` to avoid blocking. In non-browser (SSG) environments, preloading SHALL happen immediately during `RouterView._on_set_parent()`.

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
- **AND** other lazy routes SHALL continue to be preloaded without interruption
- **AND** subsequent navigation to that route SHALL attempt resolution again via `_resolve()`

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
`RouterView` SHALL extend `DynamicElement` instead of `Element`. This removes the unnecessary `<div webcompy-routerview>` wrapper from the DOM and provides the `_on_set_parent()` lifecycle hook. In non-browser environments, `_on_set_parent()` SHALL schedule auto-preload. In browser environments, auto-preload SHALL be deferred until after the initial render completes and the loading indicator is removed.

#### Scenario: RouterView does not produce a DOM node
- **WHEN** a `RouterView` is rendered in the browser
- **THEN** it SHALL NOT create a `<div>` element
- **AND** the matched page component SHALL be positioned directly in the parent node
- **AND** `RouterView._on_set_parent()` SHALL initialize children and, in non-browser environments, schedule lazy route preloading

#### Scenario: RouterView SSG output
- **WHEN** `generate_html()` produces output containing a `RouterView`
- **THEN** the output SHALL NOT contain a `<div webcompy-routerview>` wrapper
- **AND** the route content SHALL be rendered directly without an extra `<div>`

### Requirement: RouterView shall render its chain level by ancestor depth
`RouterView` SHALL determine its depth by counting `RouterView` ancestors in the element tree (computed at match time, not in `_on_set_parent`, where the parent chain is incomplete during component setup). A depth-N `RouterView` SHALL render the component at chain level N of the current match. If the chain has N or fewer levels, the `RouterView` SHALL render nothing (not an error). Multiple `RouterView`s at the same depth SHALL each render their level of the single current match.

#### Scenario: Layout with nested view
- **WHEN** the URL is `/docs/guide` matching chain `[DocsLayout, GuidePage]`
- **THEN** the root `RouterView` (depth 0) SHALL render `DocsLayout`
- **AND** the `RouterView` inside `DocsLayout` (depth 1) SHALL render `GuidePage`

#### Scenario: View deeper than chain renders empty
- **WHEN** a depth-2 `RouterView` exists but the match chain has 2 levels
- **THEN** it SHALL render nothing and SHALL NOT raise

### Requirement: Chain levels shall be reused only on identical match
For each chain level, the mounted component instance SHALL be preserved across a navigation only when the level's route record, the accumulated `path_params` (levels 0..N), and the `query` dict are all identical to the previous navigation. Otherwise, that level and all deeper levels SHALL be destroyed and re-created. Preservation SHALL use signal identity (the same instance object), so no re-render or setup re-execution occurs for preserved levels. When a level is re-created, its descendants SHALL NOT be instantiated transiently before the remounting ancestor destroys the old subtree — each level SHALL be re-created at most once per navigation.

#### Scenario: Sibling navigation preserves parent
- **WHEN** navigating from `/docs/guide` to `/docs/api` (chain level 0 identical: `DocsLayout`, no params, same query)
- **THEN** the `DocsLayout` instance SHALL be preserved (its state, scroll, and open UI persist)
- **AND** level 1 SHALL be destroyed and re-created as `ApiPage` (setup runs)

#### Scenario: Param change remounts the level
- **WHEN** navigating from `/docs/api/x` to `/docs/api/y` with route `/docs/api/{name}`
- **THEN** level 0 (`DocsLayout`) SHALL be preserved (its accumulated params are unchanged)
- **AND** level 1 (`ApiPage`) SHALL be destroyed and re-created with fresh context (setup re-runs)

#### Scenario: Query change remounts
- **WHEN** navigating from `/docs/guide?tab=a` to `/docs/guide?tab=b`
- **THEN** the level rendering `GuidePage` SHALL be remounted (query is part of context identity)

#### Scenario: Ancestor param change remounts descendants
- **WHEN** navigating from `/users/1/docs` to `/users/2/docs`
- **THEN** the `/users/{uid}` level and ALL deeper levels SHALL be remounted

#### Scenario: Descendant levels are re-created once per navigation
- **WHEN** a query or ancestor-param change remounts an ancestor level
- **THEN** the ancestor and each descendant level SHALL be re-created exactly once
- **AND** no transient duplicate instance SHALL be created for any descendant level (setup SHALL NOT run twice for the same navigation)

### Requirement: Nested routes shall integrate with lazy loading, hooks, and SSG
Lazy components (`lazy()`) SHALL be allowed at any tree level; preloading SHALL traverse the whole tree. Router hooks SHALL fire once per navigation (not per level). `Router.__routes__` SHALL remain a flat list of full leaf paths in the existing 5-tuple shape so that static site generation enumerates all nested paths without changes to the CLI.

#### Scenario: Lazy child preloads on hover
- **WHEN** a child route uses `lazy("app.pages.guide:GuidePage", __file__)` and a `RouterLink` to its full path is hovered
- **THEN** the child module SHALL preload (existing hover behavior, resolved through the flattened routes)

#### Scenario: Hooks fire once
- **WHEN** navigating from `/docs/guide` to `/docs/api`
- **THEN** `before_route_change` and `after_route_change` SHALL each fire exactly once

#### Scenario: SSG renders nested paths
- **WHEN** `webcompy generate` runs with history-mode nested routes `/docs` → `["", "/guide"]`
- **THEN** static HTML SHALL be produced for `/docs/` and `/docs/guide/`, each with the full chain rendered

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

### Requirement: Router receives HistoryPort via constructor
`Router` SHALL accept a `HistoryPort` instance as a constructor parameter rather than creating a `Location` internally.

#### Scenario: Router constructed with HistoryPort
- **WHEN** `Router(pages..., history=history_port)` is instantiated
- **THEN** `self._history` SHALL reference the provided `HistoryPort`
- **AND** `Router.__set_path__` SHALL delegate to `self._history.navigate()`

### Requirement: Location class removed
The `Location` class SHALL be removed. All path state and navigation functionality SHALL be provided by `HistoryPort`.

#### Scenario: HistoryPort replaces Location references
- **WHEN** code previously used `Location.__set_path__`
- **THEN** it SHALL use `HistoryPort.navigate()` instead

### Requirement: _browser/ directory removed
The `webcompy/_browser/` directory SHALL be fully deleted. All remaining `browser` references in Router files SHALL be migrated to `context.window.*` or port injection.

#### Scenario: _browser/ directory does not exist
- **WHEN** the framework is installed and imported
- **THEN** `webcompy/_browser/` SHALL not exist on disk

#### Scenario: Router files use context.window instead of browser
- **WHEN** Router files need window-level browser APIs
- **THEN** they SHALL access them via `pyscript.context.window` instead of the removed `browser` object

### Requirement: use_router shall provide typed router access via DI
`use_router()` SHALL be a composable function that returns the Router instance by calling `inject()` with the framework's router DI key. It SHALL raise `InjectionError` if no router is provided (i.e., the app was created without a router).

#### Scenario: Using use_router in a component
- **WHEN** a component setup function calls `use_router()`
- **AND** the app was created with a router
- **THEN** the Router instance SHALL be returned

#### Scenario: Using use_router without a router
- **WHEN** a component setup function calls `use_router()`
- **AND** the app was created without a router
- **THEN** `InjectionError` SHALL be raised

#### Scenario: use_router is a thin inject wrapper
- **WHEN** a developer inspects the `use_router` implementation
- **THEN** it SHALL be equivalent to `return inject(RouterKey)` where `RouterKey` is the framework's public router DI key
