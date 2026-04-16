# Application Bootstrapping

## Purpose

Bootstrapping is the process by which a WebComPy application comes to life. It bridges the gap between the developer's component definitions and the running application in the browser: connecting the root component to the DOM, initializing the router if one exists, setting up reactive head management, and removing the loading screen once the app is ready.

On the server side, bootstrapping enables static site generation — rendering the component tree to HTML strings that can be served without browser execution.

## Requirements

### Requirement: The application entry point shall connect a root component to the DOM
`WebComPyApp` SHALL accept a root component and optional router, and create an application root that renders the component into the `#webcompy-app` DOM element.

#### Scenario: Starting an app without a router
- **WHEN** a developer creates `WebComPyApp(root_component=MyApp)`
- **THEN** `MyApp` SHALL be rendered inside `<div id="webcompy-app">`
- **AND** the app SHALL function as a single-page application with no routing

#### Scenario: Starting an app with a router
- **WHEN** a developer creates `WebComPyApp(root_component=MyApp, router=my_router)`
- **THEN** the router SHALL be connected to `RouterView` and `RouterLink`
- **AND** URL-based navigation SHALL work

### Requirement: The application shall hydrate pre-rendered content
When the browser finds existing DOM content inside `#webcompy-app`, the application SHALL reuse those nodes rather than recreating them, enabling fast initial page loads.

#### Scenario: Hydrating a server-rendered page
- **WHEN** the browser loads a pre-rendered page containing `#webcompy-app`
- **THEN** the application SHALL adopt existing DOM nodes
- **AND** reactive bindings SHALL be attached to those nodes
- **AND** no visible flash or content duplication SHALL occur

### Requirement: The loading indicator shall be removed on first render
When the application finishes its first render, the `#webcompy-loading` element SHALL be removed from the DOM, revealing the fully rendered application.

#### Scenario: Initial page load
- **WHEN** a user opens a WebComPy app
- **THEN** a loading spinner SHALL be visible while PyScript initializes
- **AND** once the app renders, the spinner SHALL disappear

### Requirement: The application shall manage the document head reactively
When components set the document title or meta tags, those changes SHALL be reflected in the browser's document head. When a component is destroyed, its head entries SHALL be removed, and the most recently set title SHALL take effect.

#### Scenario: A page component sets the title
- **WHEN** a page component calls `context.set_title("User Profile")`
- **THEN** the browser tab title SHALL update to "User Profile"
- **WHEN** the user navigates to a different page
- **THEN** the previous page's title SHALL be removed and the new page's title SHALL take effect

### Requirement: The application shall support scoped CSS injection
All registered components' scoped CSS SHALL be collected and injected into the document as a single `<style>` block during rendering.

#### Scenario: Rendering multiple components with scoped styles
- **WHEN** components `A` and `B` each define scoped CSS
- **THEN** both styles SHALL appear in a single `<style>` element in the document head
- **AND** each style SHALL only affect elements within its respective component

### Requirement: Static site generation shall produce complete HTML pages
The CLI SHALL render the application to HTML strings for each route, including PyScript bootstrapping code, dependency packages, and the loading screen.

#### Scenario: Generating a static site
- **WHEN** the generate command is run
- **THEN** each route SHALL produce an `index.html` with pre-rendered content
- **AND** the HTML SHALL include `<script>` tags for PyScript and package configuration
- **AND** a loading screen SHALL be shown until PyScript finishes initialization