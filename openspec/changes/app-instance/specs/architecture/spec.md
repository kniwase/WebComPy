## MODIFIED Requirements

### Requirement: The application entry point shall connect all subsystems
`WebComPyApp` SHALL serve as the single entry point that wires together the root component, the router, and the reactive head management system. It SHALL own its configuration (`AppConfig`), state (`HeadPropsStore`, `ComponentStore`), and lifecycle methods (`run`, `serve`, `generate`). Developers SHALL only need to provide a root component and optionally a router and config — the framework handles all internal wiring.

#### Scenario: Creating a minimal application with config
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, config=AppConfig(base_url="/app/"))`
- **THEN** the reactive system, component system, and element system SHALL be wired together
- **AND** `app.run()` SHALL produce the full UI in the browser
- **AND** `app.serve()` SHALL start the dev server
- **AND** `app.asgi_app` SHALL return a mountable ASGI application

#### Scenario: Creating an application with routing
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, router=router, config=AppConfig(base_url="/app/"))`
- **THEN** `RouterView` and `RouterLink` SHALL be connected to the router
- **AND** URL changes SHALL trigger reactive UI updates

### Requirement: The project structure shall be discoverable by convention
A WebComPy project SHALL follow a specific directory layout. The CLI SHALL support both the existing convention (a `webcompy_config.py` with a `WebComPyConfig` instance, and an app package with a `bootstrap.py`) and the new pattern (an app module with a `WebComPyApp` instance that owns its `AppConfig`). The new pattern does not require `webcompy_config.py`.

#### Scenario: Starting the dev server with new pattern
- **WHEN** a developer runs `app.serve(dev=True)` directly from Python
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
**Reason**: Replaced by `AppConfig`, `ServerConfig`, and `GenerateConfig` dataclasses with validated fields and sensible defaults.
**Migration**: Use `AppConfig(base_url=..., dependencies=..., assets=...)` instead of `WebComPyConfig(app_package=..., base=..., dependencies=..., assets=...)`. Deployment-specific settings use `ServerConfig` and `GenerateConfig` passed to `app.serve()` and `app.generate()` respectively.