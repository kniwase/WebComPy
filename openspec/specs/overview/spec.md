# Overview

## Purpose

WebComPy is a Python front-end framework that runs entirely in the browser via PyScript. It enables developers to build single-page web applications using Python — for state management, UI composition, routing, and event handling — without writing JavaScript.

A front-end framework exists to solve a fundamental problem: as web applications grow beyond simple pages, developers need structured ways to manage state, compose UIs, handle navigation, and keep the interface consistent with the underlying data. Without a framework, these concerns become tangled — manual DOM updates, ad-hoc state variables, and fragile event handlers that break when the application changes.

WebComPy's core promise is **reactivity by default**: when data changes, everything that depends on it updates automatically. This covers primitive values, computed derivations, collection mutations, conditional renderings, and async results. The developer describes what the UI should look like for a given state, and the framework handles the rest — no manual DOM manipulation, no event-driven update orchestration, no state synchronization bugs.

**What WebComPy does not yet provide:** Other frontend frameworks commonly offer dependency injection (Vue's provide/inject, React's Context) for sharing state across the component tree without prop drilling, and plugin systems for extending framework behavior. WebComPy also lacks fine-grained DOM patching — when a list changes, the entire list is regenerated rather than reconciling individual items with keys.

## Requirements

### Requirement: WebComPy shall enable building web applications entirely in Python
Developers SHALL be able to define signal state, compose UIs, handle user events, and manage navigation entirely in Python, without writing JavaScript. The application SHALL run in the browser via PyScript at runtime, and SHALL produce deployable static sites for production.

#### Scenario: Building a signal counter component
- **WHEN** a developer creates a component with a `Signal(0)` counter and increments it on a button click
- **THEN** the displayed count SHALL update automatically without manual DOM manipulation
- **AND** the application runs in the browser via PyScript without a server at runtime

### Requirement: Signal state changes shall automatically propagate to the UI
When a signal value changes, all parts of the UI that depend on that value — text content, attributes, computed derivations, list renderings, conditional branches — SHALL update without the developer writing any update logic. This is the foundational guarantee that makes declarative UI possible.

#### Scenario: Displaying a computed value
- **WHEN** a `Computed` derives its value from one or more `Signal` sources
- **AND** any source value changes
- **THEN** the computed value SHALL recalculate automatically
- **AND** any UI element bound to the computed value SHALL update

### Requirement: Components shall encapsulate markup, behavior, and styling
A component SHALL be a self-contained unit with its own template, lifecycle hooks, and scoped CSS. Components SHALL be composable through props and slots, and their styles SHALL NOT leak to other components.

#### Scenario: Using a component within another component
- **WHEN** a developer uses `MyButton` inside `MyForm`'s template
- **THEN** `MyButton`'s scoped CSS SHALL NOT affect elements outside `MyButton`
- **AND** `MyForm` can pass data to `MyButton` via props

### Requirement: Navigation shall be synchronized with application state
The browser URL SHALL determine which page is displayed, and user navigation (link clicks, browser back/forward) SHALL update both the URL and the UI without a full page reload. Developers SHALL be able to choose between hash mode and history mode.

#### Scenario: Navigating between pages
- **WHEN** a user clicks a `RouterLink`
- **THEN** the browser URL SHALL update without a full page reload
- **AND** the page component matching the new URL SHALL be displayed
- **AND** the previous page component SHALL be destroyed

### Requirement: Asynchronous operations shall integrate with the signal system
Developers SHALL be able to start async operations (HTTP requests, long computations) and have their results automatically reflected in the UI when they resolve, with loading and error states accessible through the signal system.

#### Scenario: Fetching data from an API
- **WHEN** a developer creates an `AsyncResult` via `useAsyncResult(fetch_func)` inside a component setup
- **THEN** the UI SHALL show a loading state (`AsyncResult.is_loading`) until the operation completes
- **AND** when the operation succeeds, the UI SHALL update with the result (`AsyncResult.data.value`)
- **AND** when the operation fails, the UI SHALL be able to detect the error (`AsyncResult.is_error`, `AsyncResult.error.value`)

### Requirement: The framework shall support a complete development-to-deployment lifecycle
The CLI SHALL provide hot-reload development, static site generation, and project scaffolding. The same application code SHALL work in both environments without modification.

#### Scenario: Developing and deploying an application
- **WHEN** a developer runs the dev server, makes changes, and then generates a static site
- **THEN** the same application code SHALL work in both environments
- **AND** the generated static site SHALL be deployable to any static hosting service