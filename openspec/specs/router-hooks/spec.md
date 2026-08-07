# Router Hooks

## Purpose

Router hooks provide navigation lifecycle callbacks that enable plugins to intercept route changes, implement navigation guards, track page views for analytics, and handle routing errors.

## Requirements

### Requirement: The router shall support navigation guard callbacks

The `Router` class SHALL expose `before_route_change`, `after_route_change`, and `on_route_error` as instance attributes initialized in `__init__()`. Plugins and other code SHALL be able to append callables. For `before_route_change`, callbacks receive current and target paths and return `False` to cancel navigation. For `on_route_error`, callbacks receive the exception and return `True` to suppress propagation.

#### Scenario: Authentication guard cancels navigation
- **WHEN** a plugin appends `guard(from_path, to_path)` to `router.before_route_change`
- **AND** `guard` returns `False` for an unauthenticated user
- **AND** the user clicks `RouterLink` to `/admin`
- **THEN** the navigation SHALL be cancelled
- **AND** `after_route_change` callbacks SHALL NOT fire

#### Scenario: Multiple guards run in order
- **WHEN** `router.before_route_change` contains `[guard_a, guard_b]`
- **AND** `guard_a` returns `False`
- **THEN** `guard_b` SHALL NOT be called (short-circuit on first cancel)
- **AND** the navigation SHALL be cancelled

#### Scenario: All guards pass
- **WHEN** `router.before_route_change` contains `[guard_a, guard_b]`
- **AND** both return `None` or `True`
- **THEN** the navigation SHALL proceed
- **AND** the URL SHALL update
- **AND** `after_route_change` callbacks SHALL fire

### Requirement: The router shall support after-navigation callbacks

The `Router` class SHALL expose an `after_route_change` callback list. Callbacks SHALL receive the new path after a successful navigation.

#### Scenario: Analytics page view tracking
- **WHEN** a plugin appends `track_page_view(path)` to `router.after_route_change`
- **AND** the user navigates to `/about`
- **THEN** `track_page_view` SHALL be called with `"/about"` after the route is resolved
- **AND** the callback SHALL NOT be called if `before_route_change` cancelled the navigation

#### Scenario: Multiple after-navigation callbacks
- **WHEN** `router.after_route_change` contains multiple callbacks
- **THEN** all callbacks SHALL be called in registration order
- **AND** each SHALL receive the new path

### Requirement: The router shall support error callbacks

The `Router` class SHALL expose an `on_route_error` callback list as an instance attribute. Callbacks SHALL receive the exception and return `True` to suppress propagation, or `False`/`None` to allow the exception to propagate normally.

#### Scenario: Handling a routing error
- **WHEN** a route resolution raises `WebComPyRouterException`
- **AND** `router.on_route_error` contains a handler that returns `True`
- **THEN** the handler SHALL be called with the exception
- **AND** the exception SHALL be suppressed (application SHALL NOT crash)

#### Scenario: Error handler does not suppress
- **WHEN** a route resolution raises `WebComPyRouterException`
- **AND** `router.on_route_error` contains a handler that returns `False` or `None`
- **THEN** the exception SHALL propagate normally

### Requirement: Router hooks shall dispatch synchronously

Navigation hooks follow a **sync fast-path** contract: when every `before_route_change` guard returns a non-awaitable value, `Router.__set_path__()` SHALL complete the entire navigation synchronously — guard evaluation, URL update, signal change, and `after_route_change` callbacks all finish before `__set_path__()` returns. When a guard returns an awaitable, the framework SHALL await it asynchronously (via the framework's dual-environment async resolver) and complete the navigation asynchronously; `after_route_change` callbacks SHALL fire only after the guard chain resolves and the navigation applies.

#### Scenario: Sync fast-path remains synchronous
- **WHEN** all guards are synchronous and allow the navigation
- **THEN** the URL update, signal change, and `after_route_change` callbacks SHALL complete before `__set_path__()` returns

#### Scenario: Async guard defers completion
- **WHEN** a `before_route_change` guard returns a coroutine
- **THEN** the navigation SHALL NOT apply until the coroutine resolves
- **AND** `after_route_change` callbacks SHALL fire after resolution, only if the navigation was allowed

### Requirement: Router hooks shall be compatible with both hash and history modes

Navigation hook callbacks SHALL be invoked for both hash mode (`#/path`) and history mode (`/path`) navigations.

#### Scenario: Guard in hash mode
- **WHEN** `Router(mode="hash")` has a `before_route_change` guard
- **AND** the user navigates via `RouterLink`
- **THEN** the guard SHALL be called with the hash-formatted paths
- **AND** the guard SHALL work identically to history mode

### Requirement: Router hooks shall be accessible to plugins during initialization

The `WebComPyApp` SHALL expose the current `Router` instance as `app.router` so plugins can access it during `on_app_init()`. The `Router` instance SHALL be stored on the app before `PluginManager.init_all()` is called, ensuring plugins can register hook callbacks.

#### Scenario: Auth plugin registers guard
- **WHEN** an auth plugin's `on_app_init(app)` calls `app.router.before_route_change.append(auth_guard)`
- **THEN** the guard SHALL be active for all subsequent navigations
- **AND** the guard SHALL persist for the application's lifetime

### Requirement: Request-scoped router clones shall inherit hook registrations

`Router._clone_for_request()` SHALL copy the `before_route_change`, `after_route_change`, and `on_route_error` registrations from the source router into the clone as independent lists. Every `RenderContext` injects such a clone into the component tree, so hooks registered on `app.router` (e.g., by plugins during `on_app_init`) SHALL be invoked for navigations through the injected per-request router.

#### Scenario: Guard registered on app.router fires on injected router navigation
- **WHEN** a plugin appends `guard(from_path, to_path)` to `app.router.before_route_change` before any `RenderContext` is created
- **AND** a `RenderContext` is created and `__set_path__` is called on its injected router
- **THEN** `guard` SHALL be called with the current and target paths
- **AND** appending callbacks to the clone afterwards SHALL NOT mutate the source router's hook lists (and vice versa)

### Requirement: Guards shall support redirect results

A `before_route_change` guard MAY return a string path. The router SHALL cancel the current navigation and start a fresh navigation attempt to that path, re-running the full guard chain on the redirect target. The redirect SHALL be committed with history replacement (`replace_url`) rather than a push, so the intermediate URL never occupies a history entry. Redirect chains SHALL be bounded: after more than 10 redirects for one logical navigation, the router SHALL raise `WebComPyRouterException` through `on_route_error`.

#### Scenario: Login redirect
- **WHEN** a guard returns `"/login"` for a navigation to `/admin`
- **THEN** the navigation to `/admin` SHALL be cancelled
- **AND** a navigation to `/login` SHALL be attempted with the full guard chain
- **AND** the browser history entry SHALL be replaced rather than pushed

#### Scenario: Redirect loop protection
- **WHEN** guards redirect `/a` → `/b` → `/a` → ... indefinitely
- **THEN** after 10 redirects the router SHALL raise `WebComPyRouterException` via `on_route_error`

### Requirement: Concurrent async navigations shall resolve latest-wins

Each navigation attempt SHALL carry a monotonic token. When a new navigation begins while a previous async guard chain is still pending, the pending chain SHALL be superseded: upon continuation it SHALL NOT update the URL, SHALL NOT change the route signal, and SHALL NOT fire `after_route_change`. Superseded user guard code that is already running SHALL run to completion (no coroutine cancellation); only its navigation effects are abandoned. Synchronous chains SHALL complete atomically and can never be superseded mid-flight.

#### Scenario: Rapid double navigation
- **GIVEN** navigation A to `/slow` is pending on an async guard
- **WHEN** navigation B to `/fast` starts and completes
- **AND** navigation A's guard later resolves as allowed
- **THEN** the current route SHALL remain `/fast`
- **AND** A's `after_route_change` callbacks SHALL NOT fire

### Requirement: Guard exceptions shall cancel the navigation and route to on_route_error

A guard that raises — synchronously or from an awaited coroutine — SHALL cancel the navigation. The exception SHALL be passed to `router.on_route_error` handlers (returning `True` suppresses); unsuppressed async-guard exceptions SHALL be routed to the framework's async error pipeline.

#### Scenario: Async guard failure
- **WHEN** an awaited guard raises `RuntimeError`
- **THEN** the navigation SHALL NOT apply
- **AND** `on_route_error` handlers SHALL receive the exception

### Requirement: The router shall own browser URL updates after guards pass

The browser address bar SHALL be updated only after the guard chain allows the navigation: push for normal navigations, replace for redirects. A cancelled or superseded navigation SHALL NOT modify the address bar. Programmatic path changes (`app.set_path` / router navigation without `RouterLink`) SHALL update the address bar identically to link-initiated ones. `before_route_change` guards SHALL receive clean app-internal paths (base-url and hash prefixes stripped, trailing-slash normalized). Browser history traversal (popstate) SHALL NOT run guards, as today.

#### Scenario: Cancelled navigation leaves address bar unchanged
- **WHEN** a guard cancels a `RouterLink` navigation to `/admin`
- **THEN** the browser address bar SHALL remain on the current URL

#### Scenario: Programmatic navigation updates address bar
- **WHEN** app code calls `app.set_path("/about")` and guards pass
- **THEN** the browser address bar SHALL show the `/about` URL
