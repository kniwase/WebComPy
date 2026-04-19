## MODIFIED Requirements

### Requirement: The application entry point shall connect a root component to the DOM
`WebComPyApp` SHALL accept a root component, optional router, and optional `AppConfig`, and create an application root that renders the component. The `run(selector)` method SHALL be the browser entry point, accepting a CSS selector (default `"#webcompy-app"`). The `__component__` property SHALL emit a `DeprecationWarning` and return the internal `AppDocumentRoot`.

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

#### Scenario: Accessing the deprecated __component__ property
- **WHEN** a developer accesses `app.__component__`
- **THEN** a `DeprecationWarning` SHALL be emitted
- **AND** the `AppDocumentRoot` SHALL be returned for backward compatibility

### Requirement: The application shall hydrate pre-rendered content
When the browser finds existing DOM content inside the mount element, the application SHALL reuse those nodes rather than recreating them, enabling fast initial page loads.

#### Scenario: Hydrating a server-rendered page
- **WHEN** the browser loads a pre-rendered page and `app.run()` is called
- **THEN** the application SHALL adopt existing DOM nodes within the mount element
- **AND** reactive bindings SHALL be attached to those nodes
- **AND** no visible flash or content duplication SHALL occur

### Requirement: The loading indicator shall be removed on first render
When the application finishes its first render, the `#webcompy-loading` element SHALL be removed from the DOM, revealing the fully rendered application.

#### Scenario: Initial page load with app.run()
- **WHEN** a user opens a WebComPy app and `app.run()` is called
- **THEN** a loading spinner SHALL be visible while PyScript initializes
- **AND** once the app renders, the spinner SHALL disappear