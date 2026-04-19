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

### Requirement: The application shall manage the document head reactively
When components set the document title or meta tags, those changes SHALL be reflected in the browser's document head. When a component is destroyed, its head entries SHALL be removed, and the most recently set title SHALL take effect. Head props SHALL be accessed via DI injection using `_HEAD_PROPS_KEY`, and each app SHALL have its own `HeadPropsStore` in its DI scope.

#### Scenario: A page component sets the title
- **WHEN** a component calls `context.set_title("My Page")`
- **THEN** the document title SHALL update to "My Page"
- **WHEN** the user navigates to a different page
- **THEN** the previous page's title SHALL be removed and the new page's title SHALL take effect

### Requirement: The application shall support scoped CSS injection
All registered components' scoped CSS SHALL be collected and injected into the document as a single `<style>` block during rendering. Each app SHALL have its own `ComponentStore` in its DI scope, ensuring style collection is isolated per app.

#### Scenario: Rendering multiple components with scoped styles
- **WHEN** components `A` and `B` each define scoped CSS
- **THEN** both styles SHALL appear in a single `<style>` element in the document head
- **AND** each style SHALL only affect elements within its respective component

### Requirement: Multiple WebComPy applications shall coexist without interference
Each `WebComPyApp` instance SHALL have its own DI scope, Router, HeadPropsStore, ComponentStore, and deferred rendering state. Module-level global singletons (`_root_di_scope`, `_default_component_store`, `RouterView._instance`) SHALL NOT be used for app-scoped state. The `_defer_after_rendering_depth` and `_deferred_after_rendering_callbacks` state SHALL be owned by the app instance, not by module globals.

#### Scenario: Two apps on the same page
- **WHEN** two `WebComPyApp` instances are created with different root components and both call `app.run()`
- **THEN** each app SHALL render into its own mount element
- **AND** each app SHALL have its own Router, ComponentStore, HeadPropsStore, and DI scope
- **AND** components in one app SHALL NOT see DI values from the other
- **AND** setting the title in one app SHALL NOT affect the other

#### Scenario: Two apps in the same server process
- **WHEN** two `WebComPyApp` instances are created and both call `app.serve()` or `app.generate()`
- **THEN** each app SHALL produce independent output
- **AND** each app SHALL have its own configuration, routes, and DI scope

### Requirement: Static site generation shall produce complete HTML pages
The CLI SHALL render the application to HTML strings for each route, including PyScript bootstrapping code, dependency packages, and the loading screen. The generated bootstrap code SHALL use `app.run()` instead of the deprecated `app.__component__.render()` pattern.

#### Scenario: Generating a static site
- **WHEN** the generate command is run
- **THEN** each route SHALL produce an `index.html` with pre-rendered content
- **AND** the HTML SHALL include `<script>` tags for PyScript and package configuration
- **AND** a loading screen SHALL be shown until PyScript finishes initialization
- **AND** the PyScript bootstrap code SHALL call `app.run()`