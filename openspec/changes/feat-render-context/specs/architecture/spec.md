## MODIFIED Requirements

### Requirement: The framework shall operate in two environments from a single codebase

The same Python source code SHALL execute correctly both in the browser (via PyScript/Emscripten) and on the server (standard CPython). In the browser, the framework manipulates the DOM directly and responds to user interaction. On the server, it generates HTML strings for SSR. The rendering context differs between environments: the browser creates a single long-lived `RenderContext`, while the server creates and disposes a `RenderContext` per request. No application code should need to change between environments.

#### Scenario: Rendering a component in the browser
- **WHEN** a component with Signal-based state and a template is rendered in the browser
- **THEN** the component SHALL create and manage real DOM nodes via a single `RenderContext`
- **AND** signal updates SHALL modify those DOM nodes directly

#### Scenario: Rendering the same component on the server via SSR
- **WHEN** the same component is rendered during server-side rendering
- **THEN** a fresh `RenderContext` SHALL be created for the request
- **AND** the component SHALL produce an HTML string
- **AND** no DOM manipulation SHALL be attempted
- **AND** `RenderContext.dispose()` SHALL be called after rendering

#### Scenario: Rendering the same component during SSG
- **WHEN** the same component is rendered during static site generation
- **THEN** a `RenderContext` SHALL be created for each route
- **AND** `RenderContext.dispose()` SHALL be called after each route is rendered
- **AND** no state from one route SHALL leak into the next route

### Requirement: Multiple WebComPy applications shall coexist without interference

Each `WebComPyApp` instance SHALL hold only immutable definitions. Each `RenderContext` SHALL have its own DI scope, Router, and component tree. Global singletons SHALL NOT be used for request-scoped state. Module-level signal graph globals (`_active_consumer`, `_in_notification_phase`) SHALL use `ContextVar` for async-safe isolation between concurrent requests.

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