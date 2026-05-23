## MODIFIED Requirements

### Requirement: The application entry point shall connect all subsystems

`WebComPyApp` SHALL serve as the immutable definition holder that wires together the root component, the router definition, and the configuration. It SHALL NOT hold mutable rendering state — all mutable state SHALL belong to `RenderContext`, which is created per-request on the server and once in the browser. `WebComPyApp` SHALL provide a `create_render_context(path="")` method that creates a fresh `RenderContext` with all request-scoped state (DI scope, Router, AppDocumentRoot, HeadPropsStore, Server ports, Signal graph). In the browser, `app.run()` SHALL create a single `RenderContext` internally and delegate rendering to it. On the server, each SSR request SHALL create a new `RenderContext` via `create_render_context()`, render HTML, and then dispose it. Module-level fallback references (`_app_di_scope`, `_app_instance`) MAY still exist for browser environments where `ContextVar` propagation is unreliable. The `_active_app_context` ContextVar (currently set to the `WebComPyApp` instance during rendering) SHALL be set to the `RenderContext` instance instead, and its fallback `_app_instance` SHALL reference the `RenderContext` not the app. `start_defer_after_rendering()` and `end_defer_after_rendering()` SHALL delegate to `RenderContext._defer_depth` and `RenderContext._deferred_callbacks` via `_active_app_context` or the fallback. `app.di_scope` SHALL raise `AttributeError` on the server (directing users to `RenderContext.di_scope`) and SHALL be a forwarded property in the browser (delegating to the active RenderContext's DI scope).

#### Scenario: Creating a minimal application with config
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, config=AppConfig(base_url="/app/"))`
- **THEN** the app SHALL store immutable definitions only (config, root component definition, router definition, plugin classes)
- **AND** `app.run()` SHALL produce the full UI in the browser by creating a `RenderContext` internally
- **AND** `create_asgi_app(app)` SHALL return a mountable ASGI application that creates a new `RenderContext` per request

#### Scenario: Creating an application with routing
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, router=router, config=AppConfig(base_url="/app/"))`
- **THEN** the router definition (pages, mode, base URL) SHALL be stored on the app as immutable data
- **AND** each `RenderContext` SHALL create its own Router instance from the stored definition
- **AND** URL changes SHALL trigger reactive UI updates via the `RenderContext`'s Router

#### Scenario: Multiple apps in the same process
- **WHEN** two `WebComPyApp` instances are created in the same Python process
- **THEN** each app SHALL have its own immutable definitions
- **AND** `RenderContext` instances created from different apps SHALL be completely independent
- **AND** concurrent `RenderContext` instances from the same or different apps SHALL NOT share mutable state

#### Scenario: SSR request isolation
- **WHEN** `create_asgi_app(app)` is called and multiple HTTP requests arrive
- **THEN** each request SHALL create a new `RenderContext` via `app.create_render_context(path)`
- **AND** no mutable state from one request SHALL leak into another
- **AND** `RenderContext.dispose()` SHALL be called after HTML is generated

### Requirement: WebComPyApp shall forward AppDocumentRoot properties

`WebComPyApp` SHALL provide transparent access to frequently used properties from the current `RenderContext`'s `AppDocumentRoot` in the browser. The forwarded properties and methods SHALL include: `routes`, `router_mode`, `set_path`, `head`, `style`, `scripts`, `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`, `set_html_attr`, `remove_html_attr`, `html_attrs`. In the browser, these SHALL delegate to the single long-lived `RenderContext`. On the server, `WebComPyApp` SHALL NOT have these forwarded properties — server code MUST use `RenderContext` directly. `app.di_scope` SHALL raise `AttributeError` on the server indicating that `RenderContext.di_scope` should be used instead.

#### Scenario: Accessing app routes in the browser
- **WHEN** a developer accesses `app.routes` in the browser
- **THEN** the route list SHALL be returned from the browser's `RenderContext`'s Router
- **AND** the behavior SHALL be identical to the current implementation

#### Scenario: Accessing head management through RenderContext on the server
- **WHEN** a developer accesses `ctx.head` on a `RenderContext` on the server
- **THEN** the head management properties SHALL reflect the current request's state
- **AND** modifying head properties on one `RenderContext` SHALL NOT affect another `RenderContext`

#### Scenario: Accessing app.di_scope on the server raises error
- **WHEN** a developer accesses `app.di_scope` on a `WebComPyApp` in a server environment
- **THEN** an `AttributeError` SHALL be raised directing them to use `RenderContext.di_scope`