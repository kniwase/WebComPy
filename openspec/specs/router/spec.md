# Router

## Purpose

A front-end router solves a fundamental problem in single-page applications: synchronizing the browser's URL with the application's visible content. Without routing, navigating between "pages" requires a full page reload. With routing, only the relevant portion of the DOM changes while the browser URL updates, enabling a seamless user experience.

WebComPy provides two routing modes — hash mode for simple deployments (like static hosting services) and history mode for clean URLs (requiring server-side support). The router integrates with the reactive system so that URL changes automatically propagate to the UI: when a route changes, the page component updates without any manual wiring.

**What WebComPy does not yet provide:** Other frameworks support nested routes, route guards (before/after navigation hooks), and lazy-loaded route components. The `Location` object's `popstate` proxy requires manual `destroy()` calls for cleanup.

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
Developers SHALL be able to define routes that defer module import until the route is first matched, reducing initial startup time. A `lazy()` helper SHALL wrap an import path string and resolve it on demand.

#### Scenario: Defining a lazy route
- **WHEN** a developer writes `Router({"path": "/docs", "component": lazy("pages.docs:DocsPage", __file__)})`
- **THEN** the `pages.docs` module SHALL NOT be imported at startup
- **AND** on first navigation to `/docs`, the module SHALL be imported and `DocsPage` SHALL be rendered

#### Scenario: Lazy route with loading shell
- **WHEN** a developer writes `lazy("pages.docs:DocsPage", __file__, shell=LoadingShell)` and the module is not yet loaded
- **THEN** `LoadingShell` SHALL be rendered while the module is being imported
- **AND** once the module is loaded, the real component SHALL replace the shell

### Requirement: A default page shall be shown when no route matches
When the current URL does not match any defined route, the router SHALL render a default component or display "Not Found".

#### Scenario: Navigating to an undefined route
- **WHEN** the URL matches no defined route and no default component is provided
- **THEN** the text "Not Found" SHALL be displayed

#### Scenario: Navigating to an undefined route with a default component
- **WHEN** the URL matches no defined route and a default component is provided
- **THEN** the default component SHALL be rendered with the current path and query information