## MODIFIED Requirements

### Requirement: The application entry point shall connect all subsystems
`WebComPyApp` SHALL serve as the single entry point that wires together the root component, the router, and the reactive head management system. It SHALL own its configuration (`AppConfig`), state (`HeadPropsStore`, `ComponentStore`, DI scope), and the browser entry point (`run`). Server-side and SSG entry points SHALL be module-level functions (`create_asgi_app`, `run_server`, `generate_static_site`) that accept a `WebComPyApp` instance, not methods on the app object. Developers SHALL only need to provide a root component and optionally a router and config — the framework handles all internal wiring. `WebComPyApp` SHALL create a root `DIScope` and provide framework-internal services (Router, ComponentStore, HeadProps) into it. Module-level globals like `_root_di_scope` and `_default_component_store` SHALL NOT be used as the *primary* mechanism for app-scoped state. A module-level fallback reference (`_app_di_scope`, `_app_instance`) MAY exist for environments where `ContextVar` propagation is unreliable (e.g., PyScript/Emscripten), but these fallbacks hold a reference to only one app at a time. Full multi-app isolation is therefore only guaranteed in server-side contexts where `ContextVar` bindings persist reliably. Server-side and SSG entry points SHALL enter the app's DI scope for the duration of any operation that needs DI resolution (HTML generation, route rendering, etc.).

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

### Requirement: Global singletons shall be replaced by per-app or DI-provided values
`RouterView._instance`, `_default_component_store`, and `_root_di_scope` module-level globals SHALL be removed. Framework code SHALL access Router, HeadProps, and ComponentStore via `inject()` with internal DI keys. Each app instance SHALL own its state without relying on module-level globals as the *primary* mechanism. `Router._instance` and `Component._head_props` have already been removed by `feat/provide-inject`. In the browser, `inject()` and `provide()` SHALL fall back to a module-level `_app_di_scope` reference when the `_active_di_scope` `ContextVar` is unset (which occurs when PyScript invokes Python callbacks from JS event handlers that do not carry `ContextVar` bindings). Similarly, `start_defer_after_rendering()` and `end_defer_after_rendering()` SHALL fall back to a module-level `_app_instance` reference when `_active_app_context` is unset.

#### Scenario: Router is provided via DI
- **WHEN** `WebComPyApp` is created with a router
- **THEN** the router SHALL be provided into the app DI scope using internal and public keys
- **AND** `RouterView` and `TypedRouterLink` SHALL resolve it via `inject()`

#### Scenario: ComponentStore is per-app
- **WHEN** `WebComPyApp` is created
- **THEN** it SHALL create its own `ComponentStore` and provide it into the app DI scope
- **AND** `ComponentGenerator` SHALL register into the active app's store via DI when a scope is available
- **AND** no module-level `_default_component_store` global SHALL exist

#### Scenario: Head props are per-app via DI
- **WHEN** `WebComPyApp` is created
- **THEN** it SHALL create a `HeadPropsStore` and provide it into the app DI scope
- **AND** component head management SHALL use `inject()` to access it
- **AND** no `Component._head_props` ClassVar SHALL exist

#### Scenario: Two apps with independent state
- **WHEN** two `WebComPyApp` instances exist
- **THEN** each app SHALL have its own `ComponentStore`, `HeadPropsStore`, and DI scope
- **AND** scoped CSS collection SHALL be isolated per app
- **AND** title and meta settings in one app SHALL NOT affect the other

### Requirement: The project structure shall be discoverable by convention
A WebComPy project SHALL follow a specific directory layout. The CLI SHALL support both the existing convention (a `webcompy_config.py` with a `WebComPyConfig` instance, and an app package with a `bootstrap.py`) and the new pattern (an app module with a `WebComPyApp` instance that owns its `AppConfig`). The new pattern does not require `webcompy_config.py`.

#### Scenario: Starting the dev server with new pattern
- **WHEN** a developer calls `run_server(app)` directly from Python
- **THEN** the server SHALL start without requiring `webcompy_config.py`
- **AND** `AppConfig` settings SHALL be used

#### Scenario: Starting the dev server via CLI with new pattern
- **WHEN** a developer runs `python -m webcompy start --dev` and the app module exposes `app = WebComPyApp(..., config=AppConfig(...))`
- **THEN** the CLI SHALL use the `AppConfig` from the app instance
- **AND** `webcompy_config.py` SHALL not be required

#### Scenario: Starting the dev server via CLI with legacy pattern
- **WHEN** a developer runs `python -m webcompy start --dev` and only `webcompy_config.py` exists
- **THEN** the CLI SHALL discover `WebComPyConfig` and use it (with `DeprecationWarning`)

## REMOVED Requirements

### Requirement: Application configuration shall be extensible
**Reason**: Replaced by `AppConfig` dataclass with validated fields and sensible defaults. `ServerConfig` and `GenerateConfig` are retained for internal use by `create_asgi_app` and `generate_static_site` but are not passed by the developer through `WebComPyApp` lifecycle methods. Internally, the CLI converts `AppConfig` to `WebComPyConfig` for backward compatibility with existing HTML generation and wheel-building code; this conversion is an implementation detail not exposed to developers.
**Migration**: Use `AppConfig(base_url=..., dependencies=..., assets=..., app_package=...)` instead of `WebComPyConfig(app_package=..., base=..., dependencies=..., assets=...)`.