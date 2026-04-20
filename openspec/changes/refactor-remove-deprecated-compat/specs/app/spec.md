## MODIFIED Requirements

### Requirement: The application entry point shall connect a root component to the DOM
`WebComPyApp` SHALL accept a root component, optional router, and optional `AppConfig`, and create an application root that renders the component. The `run(selector)` method SHALL be the browser entry point, accepting a CSS selector (default `"#webcompy-app"`). The `__component__` property SHALL NOT exist; developers SHALL use forwarded properties (`routes`, `router_mode`, `set_path`, `head`, `style`, `scripts`, `set_title`, `set_meta`, `append_link`, `append_script`, `set_head`, `update_head`) directly.

#### Scenario: Starting an app without a router
- **WHEN** a developer creates `WebComPyApp(root_component=MyApp)` and calls `app.run()`
- **THEN** `MyApp` SHALL be rendered inside `<div id="webcompy-app">`
- **AND** the app SHALL function as a single-page application with no routing

#### Scenario: Starting an app with a router
- **WHEN** a developer creates `WebComPyApp(root_component=MyApp, router=my_router)` and calls `app.run()`
- **THEN** the router SHALL be connected to `RouterView` and `RouterLink`
- **AND** URL-based navigation SHALL work

#### Scenario: Starting an app with a custom mount selector
- **WHEN** a developer creates `WebComPyApp(root_component=MyApp)` and calls `app.run("#my-app")`
- **THEN** `MyApp` SHALL be rendered inside the element matching `#my-app`
- **AND** the app SHALL function identically to using the default selector

## REMOVED Requirements

### Requirement: Accessing the deprecated __component__ property
**Reason**: The `__component__` property was a transitional API. All necessary properties are now forwarded directly on `WebComPyApp`. Pre-release software allows breaking changes.
**Migration**: Use the forwarded properties directly: `app.routes`, `app.router_mode`, `app.set_path()`, `app.head`, `app.style`, `app.scripts`, `app.set_title()`, `app.set_meta()`, `app.append_link()`, `app.append_script()`, `app.set_head()`, `app.update_head()`.