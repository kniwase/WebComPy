## MODIFIED Requirements

### Requirement: The application entry point shall connect all subsystems
`WebComPyApp` SHALL serve as the single entry point that wires together the root component, the router, and the reactive head management system. It SHALL own its configuration (`AppConfig`), state (`HeadPropsStore`, `ComponentStore`, DI scope), and the browser entry point (`run`). Server-side and SSG entry points SHALL be module-level functions (`create_asgi_app`, `run_server`, `generate_static_site`) that accept a `WebComPyApp` instance and optional `ServerConfig`/`GenerateConfig` dataclasses. Developers SHALL only need to provide a root component and optionally a router and config — the framework handles all internal wiring. `WebComPyApp` SHALL create a root `DIScope` and provide framework-internal services (Router, ComponentStore, HeadProps) into it. Module-level globals like `_root_di_scope` and `_default_component_store` SHALL NOT be used as the *primary* mechanism for app-scoped state. A module-level fallback reference (`_app_di_scope`, `_app_instance`) MAY exist for environments where `ContextVar` propagation is unreliable (e.g., PyScript/Emscripten), but these fallbacks hold a reference to only one app at a time. Full multi-app isolation is therefore only guaranteed in server-side contexts where `ContextVar` bindings persist reliably. Server-side and SSG entry points SHALL enter the app's DI scope for the duration of any operation that needs DI resolution (HTML generation, route rendering, etc.). There is no conversion between `AppConfig` and any other config type.

#### Scenario: Creating a minimal application with config
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, config=AppConfig(base_url="/app/"))`
- **THEN** the reactive system, component system, and element system SHALL be wired together
- **AND** `app.run()` SHALL produce the full UI in the browser
- **AND** `create_asgi_app(app)` SHALL return a mountable ASGI application
- **AND** `generate_static_site(app)` SHALL produce static HTML

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
- **AND** in the browser (PyScript) environment, a module-level fallback reference exists for DI resolution when `ContextVar` bindings are lost across JS→Python callbacks; this fallback holds only the most recently created app's scope, so multi-app isolation in the browser has this limitation