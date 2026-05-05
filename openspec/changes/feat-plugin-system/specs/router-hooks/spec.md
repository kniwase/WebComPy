# Router Hooks

## Purpose

Router hooks provide navigation lifecycle callbacks that enable plugins to intercept route changes, implement navigation guards, track page views for analytics, and handle routing errors.

## ADDED Requirements

### Requirement: The router shall support navigation guard callbacks

The `Router` class SHALL expose a `before_route_change` callback list. Plugins and other code SHALL be able to append callables that receive the current path and the target path. Returning `False` from a callback SHALL cancel the navigation. Returning `None` or `True` SHALL allow it.

#### Scenario: Authentication guard cancels navigation
- **WHEN** a plugin appends `guard(from_path, to_path)` to `router.before_route_change`
- **AND** `guard` returns `False` for an unauthenticated user
- **AND** the user clicks `RouterLink` to `/admin`
- **THEN** the navigation SHALL be cancelled
- **AND** `guard` SHALL not be called for the same path

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

The `Router` class SHALL expose an `on_route_error` callback list. Callbacks SHALL receive the exception when navigation raises an error.

#### Scenario: Handling a routing error
- **WHEN** a route resolution raises `WebComPyRouterException`
- **AND** `router.on_route_error` contains a handler
- **THEN** the handler SHALL be called with the exception
- **AND** the application SHALL NOT crash

#### Scenario: No error handlers registered
- **WHEN** a route resolution raises an exception
- **AND** `router.on_route_error` is empty
- **THEN** the exception SHALL propagate normally

### Requirement: Router hooks shall dispatch synchronously

All router hooks (`before_route_change`, `after_route_change`, `on_route_error`) SHALL be dispatched synchronously during the `Location.__set_path__()` call. Async operations SHALL NOT be supported in the initial implementation.

#### Scenario: Guard runs synchronously
- **WHEN** `router.before_route_change` contains a guard
- **AND** the guard performs a synchronous check
- **THEN** the check SHALL complete before the URL updates
- **AND** the UI SHALL not show an intermediate state

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
