# Application Bootstrapping Changes

## MODIFIED Requirements

### Requirement: The application entry point shall connect a root component to the DOM

`WebComPyApp` SHALL accept a root component, optional router, and optional `AppConfig`, and create an application root that renders the component. `WebComPyApp` SHALL expose a `router` property returning the current `Router` instance (or `None` if no router is configured). During initialization, `WebComPyApp` SHALL create a `PluginManager` and initialize plugins specified in `AppConfig.plugins` before creating the `AppDocumentRoot`. The `run(selector)` method SHALL be the browser entry point, accepting a CSS selector (default `"#webcompy-app"`). `run()` SHALL call `on_app_ready(app)` on all initialized plugins before the first render. `on_app_ready` SHALL NOT be called during SSG. Forwarded properties (`routes`, `router_mode`, `set_path`, `head`, `style`, `scripts`, `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`) SHALL provide direct access to `AppDocumentRoot` functionality.

#### Scenario: Starting an app without a router
- **WHEN** a developer creates `WebComPyApp(root_component=MyApp)` and calls `app.run()`
- **THEN** `MyApp` SHALL be rendered inside `<div id="webcompy-app">`
- **AND** the app SHALL function as a single-page application with no routing
- **AND** any configured plugins SHALL be initialized and their `on_app_ready` hook SHALL be called before the first render

#### Scenario: Starting an app with a router
- **WHEN** a developer creates `WebComPyApp(root_component=MyApp, router=my_router)` and calls `app.run()`
- **THEN** the router SHALL be connected to `RouterView` and `RouterLink`
- **AND** URL-based navigation SHALL work
- **AND** plugins SHALL be able to register navigation hooks via `router.before_route_change`, `router.after_route_change`, and `router.on_route_error`

#### Scenario: Starting an app with a custom mount selector
- **WHEN** a developer creates `WebComPyApp(root_component=MyApp)` and calls `app.run("#my-app")`
- **THEN** `MyApp` SHALL be rendered inside the element matching `#my-app`
- **AND** the app SHALL function identically to using the default selector

#### Scenario: Plugin initialization during bootstrap
- **WHEN** `WebComPyApp.__init__()` is called with `config=AppConfig(plugins=["myapp:MyPlugin"])`
- **THEN** `PluginManager` SHALL discover and initialize `MyPlugin`
- **AND** `MyPlugin`'s DI providers SHALL be registered before `AppDocumentRoot` is created
- **AND** `generate_html()` SHALL include `MyPlugin`'s scripts in the output HTML

#### Scenario: Plugin on_app_ready hook
- **WHEN** `app.run()` is called in the browser
- **AND** plugins are initialized
- **THEN** `on_app_ready(app)` SHALL be called on each plugin before the first render
- **AND** plugins SHALL have access to browser APIs (`browser.document`, `browser.window`) at this point

#### Scenario: App with plugins in SSG mode
- **WHEN** `generate_static_site(app)` is called on the server
- **THEN** `generate_html()` SHALL collect scripts from all plugins
- **AND** plugin scripts SHALL be included in the generated static HTML
- **AND** no plugin lifecycle hooks (`on_app_init`, `on_app_ready`) SHALL require browser-specific APIs
