## MODIFIED Requirements

### Requirement: The application entry point shall connect all subsystems
`WebComPyApp` SHALL serve as the immutable definition holder that wires together the root component, the router, the reactive head management system via `HeadElement`, and the configuration. It SHALL NOT hold mutable rendering state — all mutable rendering state SHALL belong to `RenderContext`. App-owned diagnostic lifecycle telemetry is the sole exception: `_profile_data` SHALL be owned by the `WebComPyApp` instance and written via `_record_phase`, because the generated bootstrap script records the `pyscript_ready` timestamp before any RenderContext exists; it carries no rendering or request-scoped state. `WebComPyApp` SHALL provide a `create_render_context(path="")` method that creates a fresh `RenderContext` with all request-scoped state (DI scope, ComponentStore, HeadElement, Router). `WebComPyApp._render_context_class` SHALL allow injecting `ServerRenderContext` for server-side rendering. In the browser, `app.run()` SHALL create a single `BrowserRenderContext` internally. On the server, each SSR request SHALL create and dispose its own `ServerRenderContext`. `HeadElement` SHALL manage the `<head>` DOM element or HTML output declaratively. Module-level fallback references (`_app_di_scope`, `_app_instance`) MAY still exist for browser environments where `ContextVar` propagation is unreliable. The `_active_app_context` ContextVar SHALL reference the `RenderContext` instance, not the `WebComPyApp`. `start_defer_after_rendering()` and `end_defer_after_rendering()` SHALL delegate to `RenderContext._defer_depth` and `RenderContext._deferred_callbacks` via `_active_app_context` or the fallback. Server-side and SSG entry points (`create_asgi_app`, `run_server`, `generate_static_site`) SHALL be module-level functions in the `webcompy-cli` package that accept a `WebComPyApp` instance and optional `ServerConfig`/`GenerateConfig` dataclasses. Developers SHALL only need to provide a root component and optionally a router and config — the framework handles all internal wiring. There is no conversion between `AppConfig` and any other config type.

#### Scenario: Creating a minimal application with config
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, config=AppConfig(base_url="/app/"))`
- **THEN** the reactive system, component system, and element system SHALL be wired together
- **AND** `HeadElement` SHALL be initialized with the app's `HeadPropsStore`
- **AND** `app.run()` SHALL produce the full UI in the browser
- **AND** `create_asgi_app(app)` SHALL return a mountable ASGI application
- **AND** `generate_static_site(app)` SHALL produce static HTML with head content from `HeadElement`

#### Scenario: Creating an application with routing
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, router=router, config=AppConfig(base_url="/app/"))`
- **THEN** `RouterView` and `RouterLink` SHALL be connected to the router via DI
- **AND** URL changes SHALL trigger reactive UI updates
- **AND** the Router SHALL be provided into `app.di_scope`

#### Scenario: Multiple apps in the same process
- **WHEN** two `WebComPyApp` instances are created in the same Python process
- **THEN** each app SHALL have its own `DIScope`
- **AND** `inject()` within one app's component tree SHALL NOT resolve values from the other app's scope
- **AND** in the server/SSG environment, full isolation SHALL be guaranteed through `ContextVar` bindings
- **AND** in the browser (PyScript) environment, a module-level fallback reference exists for DI resolution when `ContextVar` bindings are lost across JS→Python callbacks; this fallback holds the most recently created live app's scope, and disposing an overlapping browser context restores the previous live scope so multi-app isolation is preserved in either disposal order

#### Scenario: App-owned profiling telemetry does not violate render-state isolation
- **WHEN** an app runs with `profile=True` in the browser or serves SSR requests on the server
- **THEN** `WebComPyApp._profile_data` MAY hold startup phase timestamps on the app instance
- **AND** all rendering state (DI scope, ComponentStore, HeadElement, Router) SHALL still belong to `RenderContext`
- **AND** concurrent SSR requests SHALL remain fully isolated from each other and from the app-owned profile data
