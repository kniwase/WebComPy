# Architecture

## Purpose

WebComPy runs the same Python codebase in two environments: the browser (via PyScript/Emscripten) where the application actually executes and manipulates the DOM, and the server (standard CPython) used for development tooling and static site generation. This dual-environment architecture is the foundational structural decision — every module, from reactive state to routing, must work identically in both contexts, while environment-specific concerns (DOM access, PyScript bootstrapping, HTML serialization) are confined to clearly separated layers.

From a developer's perspective, this means writing Python once and having it work everywhere. The framework absorbs the complexity: developers define components, state, and routing, and the framework renders to DOM nodes in the browser or HTML strings on the server, all from the same source code.

**What WebComPy does not yet provide:** Browser environment detection is binary (Emscripten or other) with no partial API availability checks — code that only needs `localStorage`, for example, cannot gracefully degrade on server-side.

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
`WebComPyApp` SHALL serve as the single entry point that wires together the root component, the router, and the reactive head management system. It SHALL own its configuration (`AppConfig`), state (`HeadPropsStore`, `ComponentStore`, DI scope), and the browser entry point (`run`). Server-side and SSG entry points SHALL be module-level functions (`create_asgi_app`, `run_server`, `generate_static_site`) that accept a `WebComPyApp` instance and optional `ServerConfig`/`GenerateConfig` dataclasses. Developers SHALL only need to provide a root component and optionally a router and config — the framework handles all internal wiring. `WebComPyApp` SHALL create a root `DIScope` and provide framework-internal services (Router, ComponentStore, HeadProps) into it. Module-level globals like `_root_di_scope` and `_default_component_store` SHALL NOT be used as the *primary* mechanism for app-scoped state. A module-level fallback reference (`_app_di_scope`, `_app_instance`) MAY exist for environments where `ContextVar` propagation is unreliable (e.g., PyScript/Emscripten), but these fallbacks hold a reference to only one app at a time. Full multi-app isolation is therefore only guaranteed in server-side contexts where `ContextVar` bindings persist reliably. Server-side and SSG entry points SHALL enter the app's DI scope for the duration of any operation that needs DI resolution (HTML generation, route rendering, etc.). There is no conversion between `AppConfig` and any other config type.

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

### Requirement: Multiple WebComPy applications shall coexist without interference
Each `WebComPyApp` instance SHALL have its own DI scope. Global singletons SHALL NOT be used for app-scoped state, enabling multiple WebComPy applications on the same page.

#### Scenario: Two apps on the same page
- **WHEN** two `WebComPyApp` instances are created with different root components
- **THEN** each app SHALL have its own Router, ComponentStore, and DI scope
- **AND** components in one app SHALL NOT see DI values from the other

### Requirement: The project structure shall be discoverable by convention
A WebComPy project SHALL follow a specific directory layout. The CLI SHALL discover the app instance using `webcompy_config.py` (which contains `app_import_path` and `app_config`) or the `--app` CLI flag. Configuration files can be placed at the project root or inside the app package directory. When `--app` is provided, the CLI derives the package from the import path and searches for `webcompy_server_config.py` in that package first, then falls back to the project root. The `webcompy_server_config.py` file is optional and contains server/SSG-only settings (`server_config`, `generate_config`).

#### Scenario: Starting the dev server with app_import_path
- **WHEN** a developer runs `python -m webcompy start` and `webcompy_config.py` at the project root defines `app_import_path = "my_app.bootstrap:app"`
- **THEN** the CLI SHALL discover the app instance
- **AND** `AppConfig` from `app.config` SHALL be used
- **AND** `ServerConfig` from `webcompy_server_config.py` SHALL be used if present

#### Scenario: Starting the dev server with --app flag
- **WHEN** a developer runs `python -m webcompy start --app my_app.bootstrap:app`
- **THEN** the CLI SHALL import `my_app.bootstrap:app`
- **AND** `webcompy_config.py` SHALL NOT be required
- **AND** `webcompy_server_config.py` SHALL be searched first as `my_app.webcompy_server_config`, then as root-level `webcompy_server_config`

#### Scenario: Minimal project structure with root-level config
- **WHEN** a project contains `webcompy_config.py` at the project root with `app_import_path` and `my_app/bootstrap.py`
- **THEN** the CLI SHALL be able to start the dev server and generate static output
- **AND** no `webcompy_server_config.py` is required (defaults are used)

#### Scenario: Project structure with package-level config
- **WHEN** a project contains `my_app/webcompy_config.py` and `my_app/webcompy_server_config.py`
- **AND** the developer runs `python -m webcompy start --app my_app.bootstrap:app`
- **THEN** the CLI SHALL discover the app via the `--app` flag
- **AND** `webcompy_server_config.py` SHALL be read from `my_app.webcompy_server_config`

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
The framework SHALL include type hints for the browser API proxy, enabling IDE autocompleted and type checking. The `browser` object SHALL be typed as `BrowserModule | None` to reflect that it is unavailable on the server, forcing developers to check before use.

#### Scenario: Using browser APIs with type safety
- **WHEN** a developer writes `if browser: browser.document.getElementById("app")`
- **THEN** the IDE SHALL provide autocompletion for `document`, `getElementById`, and other browser APIs
- **AND** the type checker SHALL understand that `browser` may be `None`