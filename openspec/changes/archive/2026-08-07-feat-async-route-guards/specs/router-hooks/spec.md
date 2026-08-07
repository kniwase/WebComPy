# Delta: router-hooks

## MODIFIED Requirements

### Requirement: Router hooks shall dispatch synchronously

Navigation hooks follow a **sync fast-path** contract: when every `before_route_change` guard returns a non-awaitable value, `Router.__set_path__()` SHALL complete the entire navigation synchronously — guard evaluation, URL update, signal change, and `after_route_change` callbacks all finish before `__set_path__()` returns. When a guard returns an awaitable, the framework SHALL await it asynchronously (via the framework's dual-environment async resolver) and complete the navigation asynchronously; `after_route_change` callbacks SHALL fire only after the guard chain resolves and the navigation applies.

#### Scenario: Sync fast-path remains synchronous
- **WHEN** all guards are synchronous and allow the navigation
- **THEN** the URL update, signal change, and `after_route_change` callbacks SHALL complete before `__set_path__()` returns

#### Scenario: Async guard defers completion
- **WHEN** a `before_route_change` guard returns a coroutine
- **THEN** the navigation SHALL NOT apply until the coroutine resolves
- **AND** `after_route_change` callbacks SHALL fire after resolution, only if the navigation was allowed

## ADDED Requirements

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

The browser address bar SHALL be updated only after the guard chain allows the navigation: push for normal navigations, replace for redirects. A cancelled or superseded navigation SHALL NOT modify the address bar. Programmatic path changes (`app.set_path` / router navigation without `RouterLink`) SHALL update the address bar identically to link-initiated ones. `before_route_change` guards SHALL receive clean app-internal paths (base-url and hash prefixes stripped). Browser history traversal (popstate) SHALL NOT run guards, as today.

#### Scenario: Cancelled navigation leaves address bar unchanged
- **WHEN** a guard cancels a `RouterLink` navigation to `/admin`
- **THEN** the browser address bar SHALL remain on the current URL

#### Scenario: Programmatic navigation updates address bar
- **WHEN** app code calls `app.set_path("/about")` and guards pass
- **THEN** the browser address bar SHALL show the `/about` URL
