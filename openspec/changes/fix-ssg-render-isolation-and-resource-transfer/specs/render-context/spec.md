## MODIFIED Requirements

### Requirement: RenderContext shall isolate all mutable rendering state per request

A `RenderContext` ABC SHALL hold all mutable runtime state needed for a single rendering operation: DI scope, Router instance, AppDocumentRoot, HeadPropsStore, ports (browser or server), Signal graph state, transfer-recording state (recorded resources and cached fetch responses used for hydration transfer), and deferred rendering state. Two concrete subclasses exist: `BrowserRenderContext` (for browser/PyScript environments) and `ServerRenderContext` (for server/SSR environments). Each `RenderContext` instance SHALL be completely independent — no mutable state SHALL be shared between instances. Component-generator registration visibility SHALL NOT depend on render context: a generator created at any point in the process SHALL be visible to every subsequently created render context of the same app.

#### Scenario: Creating a RenderContext for an SSR request
- **WHEN** `app.create_render_context(path="/users/42")` is called on the server
- **THEN** a new `ServerRenderContext` SHALL be created with a fresh DI scope, fresh Router, fresh AppDocumentRoot, fresh HeadPropsStore, fresh Server ports, reset Signal graph state, and fresh transfer-recording state
- **AND** the Router SHALL be initialized to the given path
- **AND** no mutable state from any previous `RenderContext` SHALL be present

#### Scenario: Creating a RenderContext for the browser
- **WHEN** `app.run()` is called in the browser
- **THEN** a single `BrowserRenderContext` SHALL be created internally via `create_render_context()`
- **AND** the `BrowserRenderContext` SHALL remain active for the entire browser session
- **AND** `app.run()` behavior SHALL be unchanged from the user's perspective

#### Scenario: Concurrent SSR requests are isolated
- **WHEN** two HTTP requests arrive concurrently to the same `WebComPyApp`
- **AND** `app.create_render_context(path="/page-a")` and `app.create_render_context(path="/page-b")` are called
- **THEN** each `RenderContext` SHALL render independently
- **AND** rendering `/page-a` SHALL NOT affect the output of `/page-b`
- **AND** no shared mutable state SHALL cause data contamination between the two requests

#### Scenario: Sequential requests do not contaminate transfer payloads
- **WHEN** request A loads resources or fetches responses during SSR
- **AND** request B is rendered afterwards in the same process
- **THEN** request B's transfer payload SHALL contain only the resources and fetch entries recorded by request B itself (unless a full-transfer mode is explicitly enabled)
- **AND** request B's component store SHALL still contain every component generator created while request A was rendering
