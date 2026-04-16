# Overview

## Purpose

WebComPy is a Python front-end framework that runs entirely in the browser via PyScript. It enables developers to build single-page web applications using Python as both the application language and the template language, with reactive state management, component-based architecture, and client-side routing — all without writing JavaScript.

A front-end framework exists to solve a fundamental problem: as web applications grow beyond simple pages, developers need structured ways to manage state, compose UIs, handle navigation, and keep the interface consistent with the underlying data. WebComPy addresses these concerns through a reactive system that automatically propagates data changes to the DOM, a component model that encapsulates markup and behavior, and a router that synchronizes the browser URL with application state.

The framework operates in two environments: the browser (via PyScript/Emscripten) where the application actually runs and interacts with the DOM, and the server (standard Python) used only for development tooling and static site generation. This dual-environment architecture means all DOM manipulation code must be browser-gated, while configuration and build tooling run on the server side.

## Requirements

### Requirement: WebComPy shall enable full-stack Python web application development
Developers SHALL be able to define reactive state, compose UIs, handle user events, and manage navigation entirely in Python, without writing JavaScript.

#### Scenario: Building a reactive counter component
- **WHEN** a developer creates a component with a `Reactive(0)` counter and increments it on a button click
- **THEN** the displayed count SHALL update automatically without manual DOM manipulation
- **AND** the application runs in the browser via PyScript without a server at runtime

### Requirement: WebComPy shall support static site generation for deployment
The framework SHALL provide a CLI that generates static HTML files with embedded PyScript, enabling deployment to any static hosting service.

#### Scenario: Deploying a multi-page application
- **WHEN** a developer runs the generate command with history-mode routes
- **THEN** an `index.html` SHALL be produced for each route
- **AND** a `404.html` SHALL be produced for unmatched paths
- **AND** all necessary Python wheels SHALL be packaged for browser-side execution

### Requirement: WebComPy shall provide hot-reload during development
The dev server SHALL detect code changes and trigger a browser reload, enabling fast development iteration.

#### Scenario: Editing a component during development
- **WHEN** a developer saves a Python file while the dev server is running
- **THEN** the browser SHALL reload and reflect the changes

### Requirement: Reactive state changes shall automatically propagate to the UI
When a reactive value changes, all parts of the UI that depend on that value — whether they are text content, element attributes, computed derivations, or list renderings — SHALL update without the developer writing any update logic.

#### Scenario: Displaying a computed value
- **WHEN** a `Computed` derives its value from one or more `Reactive` sources
- **AND** any source value changes
- **THEN** the computed value SHALL recalculate automatically
- **AND** any UI element bound to the computed value SHALL update

### Requirement: Components shall encapsulate markup, behavior, and styling
A component SHALL be a self-contained unit that defines its template, lifecycle hooks, and scoped CSS. Components SHALL be composable — a component can include other components as children or via slots.

#### Scenario: Using a component within another component
- **WHEN** a developer uses `MyButton` inside `MyForm`'s template
- **THEN** `MyButton`'s scoped CSS SHALL NOT affect elements outside `MyButton`
- **AND** `MyForm` can pass data to `MyButton` via props

### Requirement: Navigation shall be synchronized with application state
The router SHALL ensure that the current URL determines which page component is displayed, and that user navigation (clicking links or using browser back/forward) updates both the URL and the displayed content.

#### Scenario: Navigating to a new page
- **WHEN** a user clicks a `RouterLink`
- **THEN** the browser URL SHALL update without a full page reload
- **AND** the page component matching the new URL SHALL be displayed
- **AND** the previous page component SHALL be destroyed

### Requirement: The framework shall support both hash and history routing modes
Developers SHALL be able to choose between hash mode (`#/path`) for simple deployment and history mode (`/path`) for clean URLs with server-side support.

#### Scenario: Deploying to GitHub Pages
- **WHEN** an app is configured with hash mode
- **THEN** all routes SHALL use `#/path` format
- **AND** no server-side routing configuration is needed

#### Scenario: Deploying to a custom server
- **WHEN** an app is configured with history mode with a base URL
- **THEN** routes SHALL use `/path` format
- **AND** the base URL SHALL be stripped from route matching

### Requirement: The framework shall handle asynchronous operations reactively
Developers SHALL be able to start async operations (such as HTTP requests) and have their results automatically reflected in the UI when they resolve.

#### Scenario: Fetching data from an API
- **WHEN** a developer creates an `AsyncComputed` from an async function
- **THEN** the UI SHALL show a loading state (value is `None`) until the operation completes
- **AND** when the operation succeeds, the UI SHALL update with the result
- **AND** when the operation fails, the UI SHALL be able to detect the error