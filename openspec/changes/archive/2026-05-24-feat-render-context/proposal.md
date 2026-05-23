## Why

SSR (Server-Side Rendering) in WebComPy shares a single `WebComPyApp` instance across all HTTP requests. This means mutable state — `AppDocumentRoot._links`, `_scripts`, `HeadPropsStore`, `DIScope._children`, `_defer_depth`, `_deferred_callbacks`, the Router's current path, and module-level globals like `_active_consumer` and `_epoch` in the signal graph — is never isolated between concurrent requests. This causes data cross-contamination between users, unbounded memory growth, and potential security vulnerabilities. A request-scoped rendering context is needed so each SSR request operates on a completely fresh state.

## What Changes

- **New `RenderContext` class**: A request-scoped rendering context that holds all mutable runtime state (DI scope, Router, AppDocumentRoot, HeadPropsStore, Server ports, Signal graph state). Created per-request on the server, and created once in the browser.
- **`WebComPyApp` becomes immutable definition holder**: Retains only config, component definitions, router definitions, plugin classes, and other data that does not change across requests. Gains a `create_render_context(path="")` method.
- **`app.run()` (browser) creates a single `RenderContext` internally**: User-facing API unchanged. The method creates a `RenderContext` and delegates rendering to it.
- **Server path uses `create_render_context()` per request**: `create_asgi_app()` creates a `RenderContext` for each incoming request, renders HTML, and disposes it.
- **`RenderContext.dispose()` method**: Cleans up Signal graph state, DI scope child scopes, EffectScopes, and other request-scoped resources.
- **Signal graph `ContextVar` migration**: `_active_consumer` and `_in_notification_phase` in `_graph.py` are converted from module-level globals to `ContextVar`s, ensuring async-safe isolation.
- **Plugin lifecycle hooks**: `on_render_context_init(ctx: RenderContext)` added for per-request DI provider registration. `on_app_ready(ctx: RenderContext)` signature changed to receive `RenderContext` instead of `WebComPyApp`. `on_app_init(app: WebComPyApp)` remains unchanged.
- **Design principle**: When adding new elements, if it is uncertain whether an element should belong to `WebComPyApp` (immutable, shared) or `RenderContext` (request-scoped, isolated), prefer `RenderContext` to err on the side of safety against vulnerabilities.

## Capabilities

### New Capabilities
- `render-context`: Request-scoped rendering context that isolates all mutable state per SSR request, with lifecycle management (creation, rendering, disposal) and plugin integration hooks.

### Modified Capabilities
- `app-lifecycle`: Application bootstrapping now distinguishes between immutable definition (WebComPyApp) and request-scoped context (RenderContext). `app.run()` delegates to a RenderContext internally. Server-side rendering creates a new RenderContext per request.
- `plugin-system`: Plugin lifecycle hooks expanded with `on_render_context_init(ctx)` for per-request setup. `on_app_ready` signature changed to receive `RenderContext` instead of `WebComPyApp`.
- `architecture`: Dual-environment model updated — browser uses single long-lived RenderContext, server creates and disposes RenderContext per request. Signal graph globals migrated to ContextVar for async safety.

## Impact

- **Breaking API change**: Plugin `on_app_ready(self, app: WebComPyApp)` signature changes to `on_app_ready(self, ctx: RenderContext)`. Existing plugins will need to update.
- **Breaking internal change**: `WebComPyApp` no longer exposes `_root`, `_di_scope`, `_router`, `_defer_depth`, `_deferred_callbacks` directly. Code accessing these internals (tests, CLI, SSG) must use `RenderContext`.
- **`webcompy/app/_app.py`**: Major refactor — mutable state moved to `RenderContext`, immutable definitions remain.
- **`webcompy/app/_render_context.py`**: New file — `RenderContext` class.
- **`webcompy/cli/_server.py`**: `create_asgi_app()` and `send_html()` updated to use `RenderContext`.
- **`webcompy/cli/_html.py`**: `generate_html()` updated to accept `RenderContext`.
- **`webcompy/signal/_graph.py`**: `_active_consumer`, `_in_notification_phase` migrated to `ContextVar`.
- **`webcompy/plugin/_plugin.py`**: New `on_render_context_init` hook, `on_app_ready` signature change.
- **`webcompy/plugin/_manager.py`**: Updated to call new hooks on `RenderContext`.
- **Tests**: New tests for concurrent request isolation, memory leak detection, and existing test regression.

## Known Issues Addressed

- Module-level fallbacks (`_app_di_scope`, `_app_instance`) hold only one app reference in browser environment, limiting true multi-app isolation — `RenderContext` provides proper scoping via `ContextVar` on the server side.
- SSR state leakage between requests — `AppDocumentRoot._links`, `_scripts`, `HeadPropsStore`, and other mutable state accumulates across requests — fully resolved by creating a fresh `RenderContext` per request.

## Non-goals

- This change does not add request-level middleware or cookie/session handling to the SSR server.
- This change does not modify the browser-side rendering pipeline beyond wrapping it in a `RenderContext`.
- This change does not address multi-app isolation in the browser (multiple WebComPyApp instances on one page) — the `ContextVar` migration helps but full browser isolation is a separate concern.
- This change does not add caching or ISR (Incremental Static Regeneration) for SSR responses.