# Architecture

## Purpose

WebComPy runs the same Python codebase in two environments: the browser (via PyScript/Emscripten) where the application actually executes and manipulates the DOM, and the server (standard CPython) used for development tooling and static site generation. This dual-environment architecture is the foundational structural decision — every module, from reactive state to routing, must work identically in both contexts, while environment-specific concerns (DOM access, PyScript bootstrapping, HTML serialization) are confined to clearly separated layers.

From a developer's perspective, this means writing Python once and having it work everywhere. The framework absorbs the complexity: developers define components, state, and routing, and the framework renders to DOM nodes in the browser or HTML strings on the server, all from the same source code.

**What WebComPy does not yet provide:** The framework still relies on multiple global singletons (`Router`, `RouterView`, `ComponentStore`, `Component._head_props`) which makes testing and isolation difficult. Browser environment detection is binary (Emscripten or other) with no partial API availability checks — code that only needs `localStorage`, for example, cannot gracefully degrade on server-side.

## Requirements

### Requirement: The framework shall operate in two environments from a single codebase
The same Python source code SHALL execute correctly both in the browser (via PyScript/Emscripten) and on the server (standard CPython). In the browser, the framework manipulates the DOM directly and responds to user interaction. On the server, it generates HTML strings for static site generation. No application code should need to change between environments.

#### Scenario: Rendering a component in the browser
- **WHEN** a component with Signal-based state and a template is rendered in the browser
- **THEN** the component SHALL create and manage real DOM nodes
- **AND** signal updates SHALL modify those DOM nodes directly

#### Scenario: Rendering the same component on the server
- **WHEN** the same component is rendered during static site generation
- **THEN** the component SHALL produce an HTML string
- **AND** no DOM manipulation SHALL be attempted

### Requirement: Browser API access shall be gated by environment detection
The `browser` object SHALL be `None` on the server and a proxy to the full browser API in the browser. All code that uses browser APIs SHALL check `if browser:` before accessing them, and SHALL raise clear errors when browser APIs are unavailable on the server.

#### Scenario: Writing environment-safe component code
- **WHEN** a developer writes a component that uses browser APIs
- **THEN** the code SHALL work correctly in the browser
- **AND** server-side code (SSG, configuration) SHALL not crash due to missing browser APIs

### Requirement: The application entry point shall connect all subsystems
`WebComPyApp` SHALL serve as the single entry point that wires together the root component, the router, and the reactive head management system. Developers SHALL only need to provide a root component and optionally a router — the framework handles all internal wiring.

#### Scenario: Creating a minimal application
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp)`
- **THEN** the reactive system, component system, and element system SHALL be wired together
- **AND** `app.__component__.render()` SHALL produce the full UI

#### Scenario: Creating an application with routing
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, router=router)`
- **THEN** `RouterView` and `RouterLink` SHALL be connected to the router
- **AND** URL changes SHALL trigger reactive UI updates

### Requirement: The project structure shall be discoverable by convention
A WebComPy project SHALL follow a specific directory layout: a `webcompy_config.py` with a `WebComPyConfig` instance, and an app package with a `bootstrap.py` containing a `WebComPyApp` instance. The CLI SHALL discover these by convention, not by configuration files.

#### Scenario: Starting the dev server
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** the CLI SHALL import `webcompy_config.py` from the working directory
- **AND** find the `WebComPyConfig` instance
- **AND** import the app package's `bootstrap` module
- **AND** find the `WebComPyApp` instance

### Requirement: The CLI shall provide three distinct workflows
The framework SHALL provide three commands serving different phases of the development lifecycle: `start` for live development with hot-reload, `generate` for production static site generation, and `init` for project scaffolding.

#### Scenario: Developing with hot-reload
- **WHEN** a developer runs `python -m webcompy start --dev`
- **THEN** a local server SHALL start with SSE-based hot-reload
- **AND** changes to Python source files SHALL trigger a browser refresh

#### Scenario: Generating a production build
- **WHEN** a developer runs `python -m webcompy generate`
- **THEN** a `dist/` directory SHALL be created with pre-rendered HTML for each route
- **AND** Python wheel packages SHALL be included for browser-side execution
- **AND** the output SHALL be deployable to any static hosting service

#### Scenario: Starting a new project
- **WHEN** a developer runs `python -m webcompy init`
- **THEN** a complete project structure SHALL be created with a working example application
- **AND** the developer SHALL be able to immediately run the dev server

### Requirement: Python packages shall be delivered to the browser via wheels
The framework SHALL package itself and the application as a single bundled Python wheel. PyScript SHALL load this wheel in the browser, enabling the entire application — framework and user code alike — to run as standard Python without a JavaScript build step.

#### Scenario: Loading an application in the browser
- **WHEN** a user opens a WebComPy application in their browser
- **THEN** PyScript SHALL load a single bundled wheel containing both the webcompy framework and the application
- **AND** both `import webcompy` and the application import SHALL work
- **AND** no custom JavaScript build step SHALL be required
- **AND** no `typing_extensions` dependency SHALL be required

### Requirement: Hydration shall connect reactive bindings to pre-rendered content
When the browser loads a page with pre-rendered HTML, the framework SHALL reuse existing DOM nodes instead of recreating them, connecting reactive bindings for subsequent updates. This eliminates visible flash and layout shift on initial page load.

#### Scenario: Loading a pre-rendered page
- **WHEN** a user navigates to a WebComPy application
- **THEN** pre-rendered HTML SHALL be visible immediately
- **AND** PyScript SHALL hydrate the existing DOM nodes with reactive bindings
- **AND** no visible content flash or layout shift SHALL occur during hydration

### Requirement: Type hints shall be provided for browser APIs
The framework SHALL include type hints for the browser API proxy, enabling IDE autocompletion and type checking. The `browser` object SHALL be typed as `BrowserModule | None` to reflect that it is unavailable on the server, forcing developers to check before use.

#### Scenario: Using browser APIs with type safety
- **WHEN** a developer writes `if browser: browser.document.getElementById("app")`
- **THEN** the IDE SHALL provide autocompletion for `document`, `getElementById`, and other browser APIs
- **AND** the type checker SHALL understand that `browser` may be `None`

### Requirement: Application configuration shall be extensible
`WebComPyConfig` SHALL allow developers to customize the base URL, server port, static files directory, deployment settings, and additional Python dependencies for the browser environment.

#### Scenario: Configuring for GitHub Pages deployment
- **WHEN** a developer sets `base="/my-repo/"` and `cname="my-domain.com"`
- **THEN** all URLs SHALL be prefixed with the base path
- **AND** a `CNAME` file SHALL be generated in the dist directory
- **AND** a `.nojekyll` file SHALL be generated for GitHub Pages compatibility

#### Scenario: Adding browser dependencies
- **WHEN** a developer specifies `dependencies=["matplotlib", "numpy"]` in the config
- **THEN** those packages SHALL be included in the PyScript package configuration
- **AND** they SHALL be available for import in the browser environment