# Architecture

## Purpose

WebComPy runs Python code in two environments: the browser (via PyScript/Emscripten) where the application actually executes and manipulates the DOM, and the server (standard CPython) used for development tooling and static site generation. The dual-environment architecture is the foundational structural decision — every module in the `webcompy` core, from reactive state to routing, must work identically in both contexts, while environment-specific concerns (DOM access, PyScript bootstrapping, HTML serialization) are confined to clearly separated packages. The `webcompy-server`, `webcompy-cli`, and `webcompy-testing` packages are explicitly server-only and do NOT need to work in the browser.

From a developer's perspective, this means writing Python once and having it work everywhere. The framework absorbs the complexity: developers define components, state, and routing, and the framework renders to DOM nodes in the browser or HTML strings on the server, all from the same source code.

**What WebComPy does not yet provide:** Browser environment detection is binary (Emscripten or other) with no partial API availability checks — code that only needs `localStorage`, for example, cannot gracefully degrade on server-side.

## Requirements

### Requirement: The framework shall operate in two environments from a single codebase
The same Python source code in the `webcompy` core package SHALL execute correctly both in the browser (via PyScript/Emscripten) and on the server (standard CPython). In the browser, the framework manipulates the DOM directly and responds to user interaction. On the server, it generates HTML strings for SSR and static site generation. No application code written against the `webcompy` core should need to change between environments. The `webcompy-server`, `webcompy-cli`, and `webcompy-testing` packages are server-only — they explicitly do NOT need to function in the browser. The rendering context differs between environments: the browser creates a single long-lived `BrowserRenderContext`, while the server creates and disposes a `ServerRenderContext` per request for SSR and per route for SSG. Port provisioning is delegated to subclass `_register_ports()` methods rather than a monolithic if/else block in base `__init__`.

#### Scenario: Rendering a component in the browser
- **WHEN** a component with Signal-based state and a template is rendered in the browser
- **THEN** the component SHALL create and manage real DOM nodes via a single `BrowserRenderContext`
- **AND** signal updates SHALL modify those DOM nodes directly

#### Scenario: Rendering the same component on the server via SSR
- **WHEN** the same component is rendered during server-side rendering
- **THEN** a fresh `ServerRenderContext` SHALL be created for the request
- **AND** the component SHALL produce an HTML string
- **AND** no DOM manipulation SHALL be attempted
- **AND** `RenderContext.dispose()` SHALL be called after rendering

#### Scenario: Rendering the same component during SSG
- **WHEN** the same component is rendered during static site generation
- **THEN** a `ServerRenderContext` SHALL be created for each route
- **AND** `RenderContext.dispose()` SHALL be called after each route is rendered
- **AND** no state from one route SHALL leak into the next route

### Requirement: Browser API access shall be gated by environment detection
The `browser` object SHALL be `None` on the server and a proxy to the full browser API in the browser. All code that uses browser APIs SHALL check `if browser:` before accessing them, and SHALL raise clear errors when browser APIs are unavailable on the server. The `browser` object (from `packages/webcompy/src/webcompy/ports/_browser/_raw.py`) remains in the `webcompy` core package.

#### Scenario: Writing environment-safe component code
- **WHEN** a developer writes a component that uses browser APIs
- **THEN** the code SHALL work correctly in the browser
- **AND** server-side code (SSG, configuration) SHALL not crash due to missing browser APIs

### Requirement: The application entry point shall connect all subsystems
`WebComPyApp` SHALL serve as the immutable definition holder that wires together the root component, the router, the reactive head management system via `HeadElement`, and the configuration. It SHALL NOT hold mutable rendering state — all mutable state SHALL belong to `RenderContext`. `WebComPyApp` SHALL provide a `create_render_context(path="")` method that creates a fresh `RenderContext` with all request-scoped state (DI scope, ComponentStore, HeadElement, Router). `WebComPyApp._render_context_class` SHALL allow injecting `ServerRenderContext` for server-side rendering. In the browser, `app.run()` SHALL create a single `BrowserRenderContext` internally. On the server, each SSR request SHALL create and dispose its own `ServerRenderContext`. `HeadElement` SHALL manage the `<head>` DOM element or HTML output declaratively. Module-level fallback references (`_app_di_scope`, `_app_instance`) MAY still exist for browser environments where `ContextVar` propagation is unreliable. The `_active_app_context` ContextVar SHALL reference the `RenderContext` instance, not the `WebComPyApp`. `start_defer_after_rendering()` and `end_defer_after_rendering()` SHALL delegate to `RenderContext._defer_depth` and `RenderContext._deferred_callbacks` via `_active_app_context` or the fallback. Server-side and SSG entry points (`create_asgi_app`, `run_server`, `generate_static_site`) SHALL be module-level functions in the `webcompy-cli` package that accept a `WebComPyApp` instance and optional `ServerConfig`/`GenerateConfig` dataclasses. Developers SHALL only need to provide a root component and optionally a router and config — the framework handles all internal wiring. There is no conversion between `AppConfig` and any other config type.

#### Scenario: Creating a minimal application with config
- **WHEN** a developer writes `app = WebComPyApp(root_component=MyApp, config=AppConfig(base_url="/app/"))`
- **THEN** the reactive system, component system, and element system SHALL be wired together
- **AND** `HeadElement` SHALL be initialized with the app's `HeadPropsStore`
- **AND** `app.run()` SHALL produce the full UI in the browser
- **AND** `create_asgi_app(app)` SHALL return a mountable ASGI application
- **AND** `generate_static_site(app)` SHALL produce static HTML with head content from `HeadElement`

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
`RouterView._instance`, `_default_component_store`, and `_root_di_scope` module-level globals SHALL be removed. Framework code SHALL access Router, HeadProps, and ComponentStore via `inject()` with internal DI keys. Each app instance SHALL own its state without relying on module-level globals as the *primary* mechanism. `Router._instance` and `Component._head_props` have already been removed by `feat/provide-inject`. `HeadElement` SHALL own head rendering and scoped CSS management, with `AppDocumentRoot` delegating to it. In the browser, `inject()` and `provide()` SHALL fall back to a module-level `_app_di_scope` reference when the `_active_di_scope` `ContextVar` is unset (which occurs when PyScript invokes Python callbacks from JS event handlers that do not carry `ContextVar` bindings). Similarly, `start_defer_after_rendering()` and `end_defer_after_rendering()` SHALL fall back to a module-level `_app_instance` reference when `_active_app_context` is unset. These module-level fallback references SHALL remain in the `webcompy` core package.

#### Scenario: Head props and HeadElement are per-app
- **WHEN** `WebComPyApp` is created
- **THEN** it SHALL create a `HeadPropsStore` and provide it into the app DI scope
- **AND** it SHALL initialize a `HeadElement` that manages the `<head>` element declaratively
- **AND** component head management SHALL use `inject()` to access `HeadPropsStore`
- **AND** no `Component._head_props` ClassVar SHALL exist

#### Scenario: Two apps with independent state
- **WHEN** two `WebComPyApp` instances exist
- **THEN** each app SHALL have its own `ComponentStore`, `HeadPropsStore`, `HeadElement`, and DI scope
- **AND** scoped CSS collection SHALL be isolated per app
- **AND** title and meta settings in one app SHALL NOT affect the other

### Requirement: Multiple WebComPy applications shall coexist without interference
Each `WebComPyApp` instance SHALL have its own DI scope. Global singletons SHALL NOT be used for app-scoped state, enabling multiple WebComPy applications on the same page.

#### Scenario: Two apps on the same page (browser)
- **WHEN** two `WebComPyApp` instances are created with different root components in the browser
- **THEN** each app SHALL create its own `RenderContext` via `create_render_context()`
- **AND** each `RenderContext` SHALL have its own Router, ComponentStore, and DI scope
- **AND** components in one app SHALL NOT see DI values from the other

#### Scenario: Concurrent SSR requests to the same app (server)
- **WHEN** multiple HTTP requests arrive at a server using `create_asgi_app(app)`
- **THEN** each request SHALL create a new `RenderContext` via `app.create_render_context(path)`
- **AND** each `RenderContext` SHALL have completely independent mutable state
- **AND** disposing one `RenderContext` SHALL NOT affect any other `RenderContext`

### Requirement: The project structure shall be discoverable by convention
A WebComPy project SHALL follow a specific directory layout. The CLI SHALL discover the app instance using `webcompy_config.py` (which imports `WebComPyBuildConfig` from `webcompy_cli.config` — a legacy import path from `webcompy.cli.config` SHALL work via a shim) or the `--app` CLI flag. Configuration files can be placed at the project root or inside the app package directory. When `--app` is provided, the CLI derives the package from the import path and searches for `webcompy_server_config.py` in that package first, then falls back to the project root. The `webcompy_server_config.py` file is optional and contains server/SSG-only settings (`server_config`, `generate_config`).

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
The framework SHALL package only the `webcompy` core as a bundled Python wheel (excluding `webcompy-cli`, `webcompy-server`, and `webcompy-testing`). PyScript SHALL load this wheel in the browser, enabling the entire application — framework and user code alike — to run as standard Python without a JavaScript build step. The `_BROWSER_ONLY_EXCLUDE` mechanism is no longer needed since the package split naturally keeps server-only code out of the browser wheel.

#### Scenario: Loading an application in the browser
- **WHEN** a user opens a WebComPy application in their browser
- **THEN** PyScript SHALL load a single bundled wheel containing only the `webcompy` core framework and the application
- **AND** both `import webcompy` and the application import SHALL work
- **AND** no custom JavaScript build step SHALL be required
- **AND** no `typing_extensions` dependency SHALL be required
- **AND** no server-only packages (`webcompy-server`, `webcompy-cli`, `webcompy-testing`) SHALL be included in the wheel

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