# Render Context

## Purpose

The render context provides request-scoped state isolation for server-side rendering. Each SSR request operates on a completely fresh `RenderContext` instance, ensuring no mutable state leaks between concurrent requests. In the browser, a single `RenderContext` is created and lives for the entire page session. This eliminates data contamination, unbounded memory growth, and security vulnerabilities caused by shared mutable state across requests.

## Requirements

### Requirement: RenderContext shall isolate all mutable rendering state per request

A `RenderContext` class SHALL hold all mutable runtime state needed for a single rendering operation: DI scope, Router instance, AppDocumentRoot, HeadPropsStore, Server ports, Signal graph state, and deferred rendering state. Each `RenderContext` instance SHALL be completely independent — no mutable state SHALL be shared between instances.

#### Scenario: Creating a RenderContext for an SSR request
- **WHEN** `app.create_render_context(path="/users/42")` is called on the server
- **THEN** a new `RenderContext` SHALL be created with a fresh DI scope, fresh Router, fresh AppDocumentRoot, fresh HeadPropsStore, fresh Server ports, and reset Signal graph state
- **AND** the Router SHALL be initialized to the given path
- **AND** no mutable state from any previous `RenderContext` SHALL be present

#### Scenario: Creating a RenderContext for the browser
- **WHEN** `app.run()` is called in the browser
- **THEN** a single `RenderContext` SHALL be created internally via `create_render_context()`
- **AND** the `RenderContext` SHALL remain active for the entire browser session
- **AND** `app.run()` behavior SHALL be unchanged from the user's perspective

#### Scenario: Concurrent SSR requests are isolated
- **WHEN** two HTTP requests arrive concurrently to the same `WebComPyApp`
- **AND** `app.create_render_context(path="/page-a")` and `app.create_render_context(path="/page-b")` are called
- **THEN** each `RenderContext` SHALL render independently
- **AND** rendering `/page-a` SHALL NOT affect the output of `/page-b`
- **AND** no shared mutable state SHALL cause data contamination between the two requests

### Requirement: RenderContext shall support disposal of all request-scoped resources

`RenderContext` SHALL provide a `dispose()` method that cleans up all request-scoped resources: DI scope child disposal, EffectScope disposal, Signal graph state reset, and removal of circular references that would prevent garbage collection.

#### Scenario: Disposing a RenderContext after SSR rendering
- **WHEN** `ctx = app.create_render_context(path)` then `ctx.render_html(...)` then `ctx.dispose()` is called on the server
- **THEN** all DI scope children SHALL be disposed via `DIScope.dispose()`
- **AND** all EffectScopes SHALL be disposed (via `DIScope.dispose()` cascading to child scopes that contain effect scopes)
- **AND** Signal graph nodes owned by the disposed RenderContext's components SHALL be cleaned up via `consumer_destroy()` (called from DI scope disposal and effect scope disposal)
- **AND** no circular references that prevent garbage collection SHALL remain

#### Scenario: Disposing a RenderContext is not required in the browser
- **WHEN** `app.run()` creates a `RenderContext` in the browser
- **THEN** `dispose()` SHALL NOT be called automatically
- **AND** the `RenderContext` SHALL remain active for the browser session lifetime

### Requirement: RenderContext shall render HTML on the server

`RenderContext` SHALL provide a `render_html()` method that generates complete HTML output for the current route, including head elements, styles, scripts, and the component tree.

#### Scenario: Rendering HTML for a history-mode route
- **WHEN** `ctx = app.create_render_context(path="/users/42")` and `ctx.render_html(...)` is called
- **THEN** the rendered HTML SHALL include the component tree for the `/users/42` route
- **AND** head elements (title, meta, links) specific to that route SHALL be included
- **AND** scoped CSS for all registered components SHALL be included

#### Scenario: Rendering HTML for a hash-mode route
- **WHEN** `app.create_render_context(path="/")` is called for a hash-mode app
- **THEN** the rendered HTML SHALL use the root path `/` as the initial route
- **AND** the same HTML SHALL be produced for every request (since hash-mode uses client-side routing)

### Requirement: WebComPyApp shall retain only immutable definitions

After refactoring, `WebComPyApp` SHALL hold only configuration, component definitions, router definitions, plugin classes, and other data that does not change between requests. All mutable runtime state SHALL be moved to `RenderContext`.

#### Scenario: WebComPyApp immutability across requests
- **WHEN** `app.create_render_context(path="/a")` and `app.create_render_context(path="/b")` are called sequentially on the same `WebComPyApp`
- **THEN** `app._config` SHALL be identical before and after both calls
- **AND** `app._root_component_def` SHALL be identical before and after both calls
- **AND** `app._plugin_classes` SHALL be identical before and after both calls
- **AND** no mutable state from rendering `/a` SHALL persist when rendering `/b`

#### Scenario: Creating a WebComPyApp does not create rendering state
- **WHEN** `app = WebComPyApp(root_component=..., router=..., config=...)` is called
- **THEN** the app SHALL NOT create a DI scope, Router instance, AppDocumentRoot, or Server ports
- **AND** the app SHALL only store immutable definitions needed to create `RenderContext` instances

### Requirement: New elements shall default to RenderContext scope

When adding new elements to the framework, if it is uncertain whether an element should belong to `WebComPyApp` (immutable, shared) or `RenderContext` (request-scoped, isolated), the element SHALL be placed in `RenderContext`. This design principle errs on the side of safety against cross-request vulnerabilities.

#### Scenario: Adding a new mutable attribute
- **WHEN** a developer adds a new attribute that holds mutable state
- **AND** it is unclear whether the attribute should be on `WebComPyApp` or `RenderContext`
- **THEN** the attribute SHALL be placed on `RenderContext`

### Requirement: RenderContext shall integrate with the testing module

The `webcompy.testing` module SHALL leverage `app.create_render_context()` for SSR test isolation. `create_test_asgi_app()` SHALL create a fresh `RenderContext` per request and dispose it after rendering. `render_app_html()` SHALL be a convenience function that wraps the full `create_render_context → generate_html → dispose` pipeline. `create_browser_scope()` and `create_server_scope()` are removed — port provisioning is handled automatically by `RenderContext.__init__`. `create_test_app()` SHALL use `__dataclass_fields__` for config override filtering to correctly handle dataclass fields with `default_factory`.

#### Scenario: Testing SSR with RenderContext-based isolation
- **WHEN** `app = create_test_app(root_component=MyRoot)` and `ctx = app.create_render_context("/path")` is called in a test
- **THEN** port provisioning (server or browser) SHALL be handled automatically by `RenderContext.__init__`
- **AND** the test SHALL NOT need to manually create DI scopes or wire ports

#### Scenario: render_app_html convenience function
- **WHEN** `html = render_app_html(app, path="/about", **gen_kwargs)` is called
- **THEN** a `RenderContext` SHALL be created, `generate_html(ctx, **gen_kwargs)` SHALL be called, and `ctx.dispose()` SHALL be called in a `finally` block

#### Scenario: Testing module scope helpers are removed
- **WHEN** importing from `webcompy.testing`
- **THEN** `create_browser_scope` and `create_server_scope` SHALL NOT be importable
- **AND** `create_test_app` SHALL remain as the primary helper for creating reusable `WebComPyApp` instances

### Requirement: Signal graph globals shall use ContextVar for async safety

`_active_consumer` and `_in_notification_phase` in `_graph.py` SHALL be converted from module-level globals to `ContextVar`s, with module-level fallback globals (`_active_consumer_global`, `_in_notification_phase_global`) for PyScript environments where `ContextVar` propagation is unreliable across JS→Python callbacks. All read/write access SHALL check `ContextVar` first and fall back to the global when ContextVar is unset. `_epoch` SHALL remain a module-level global that grows monotonically and is never reset — Python integers have unlimited precision so overflow is not a concern. `reset_graph_state()` SHALL be removed; the disposal of signal graph resources is handled by `consumer_destroy()` called from DI scope and effect scope disposal, combined with ContextVar-based isolation for transient computation state.

#### Scenario: Concurrent async requests with isolated signal computation
- **WHEN** two SSR requests are being processed concurrently in an async context
- **AND** each request creates its own `RenderContext`
- **THEN** `_active_consumer` in one request SHALL NOT affect `_active_consumer` in the other
- **AND** `_in_notification_phase` in one request SHALL NOT affect `_in_notification_phase` in the other

#### Scenario: Signal graph state cleanup on RenderContext disposal
- **WHEN** `ctx.dispose()` is called after SSR rendering
- **THEN** all signal nodes belonging to disposed components SHALL be cleaned up via `consumer_destroy()`
- **AND** the `_epoch` counter SHALL continue from its current value — it SHALL NOT be reset
- **AND** no `reset_graph_state()` function SHALL exist
- **AND** `_active_consumer` and `_in_notification_phase` ContextVars SHALL revert to defaults when the async task completes

#### Scenario: PyScript fallback for ContextVar
- **WHEN** a JS event handler invokes a Python callback in PyScript
- **AND** the `ContextVar` for `_active_consumer` is unset (PyScript does not propagate ContextVars across JS→Python boundaries)
- **THEN** the accessor function SHALL fall back to the module-level global `_active_consumer_global`
- **AND** signal dependency tracking SHALL work correctly despite the ContextVar being unset