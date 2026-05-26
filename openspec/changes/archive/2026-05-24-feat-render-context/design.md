## Context

WebComPy's SSR implementation shares a single `WebComPyApp` instance across all HTTP requests. The `create_asgi_app()` function in `_server.py` creates one `WebComPyApp` and uses it for every incoming request. The `send_html()` handler mutates this shared instance (`app.set_path()`) and reads mutable state (`app.head`, `app.style`, `app.scripts`). This causes cross-request state contamination, unbounded memory growth (lists like `_links`, `_scripts` accumulate), and potential security vulnerabilities (user data leaking between requests).

On the browser side, `WebComPyApp` is instantiated once and lives for the entire page session, which is correct — a single user, a single rendering context.

The signal graph (`_graph.py`) uses module-level globals (`_active_consumer`, `_in_notification_phase`, `_epoch`) instead of `ContextVar`s, making async-safe request isolation impossible.

The plugin system passes `WebComPyApp` to hooks (`on_app_init`, `on_app_ready`), coupling plugins to the full app instance and preventing per-request plugin behavior.

## Goals / Non-Goals

**Goals:**
- Achieve complete state isolation between SSR requests — no shared mutable state, no data contamination, no memory leaks across requests
- Preserve the existing user-facing API — `app = WebComPyApp(...)` and `app.run()` must remain unchanged
- Enable plugins to participate in per-request lifecycle (DI provider registration per request)
- Make the signal graph async-safe by migrating globals to `ContextVar`
- Provide a clear, maintainable boundary between immutable app definition and request-scoped rendering state

**Non-Goals:**
- Multi-app isolation in the browser (multiple `WebComPyApp` instances on one page)
- Request-level middleware, cookie/session handling, or authentication in the SSR server
- Caching or ISR (Incremental Static Regeneration) for SSR responses
- Changing the component authoring API (`@component_template`, `Reactive`, `Computed`, etc.)
- Adding WebSocket support or real-time capabilities

## Decisions

### Decision 1: `RenderContext` class for request-scoped state

**Choice**: Introduce a `RenderContext` class that holds all mutable runtime state per request.

**Alternatives considered**:
- **Reset method on `WebComPyApp`**: Add a `reset()` method that clears mutable state between requests. Rejected because it's error-prone — forgetting to reset one attribute causes subtle bugs, and every new attribute requires a decision about whether it needs resetting.
- **`copy.deepcopy()` on `WebComPyApp`**: Deep-copy the entire app before each request. Rejected because Signal graph nodes contain circular references (producer-consumer edges) that don't deep-copy cleanly, and it copies immutable definition data unnecessarily.

**Rationale**: Creating a fresh `RenderContext` per request is the safest approach — no state leaks by construction. Nuxt 3 creates a new `NuxtApp` per request for the same reason. The cost is comparable to alternatives because the most expensive operation (building the component tree) happens per-request regardless.

### Decision 2: `WebComPyApp` retains immutable definitions only

**Choice**: Move all mutable runtime state out of `WebComPyApp` into `RenderContext`. `WebComPyApp` retains only config, component definitions, router definitions, plugin classes, and other data that doesn't change across requests.

**Classification of current `WebComPyApp` attributes**:

| Attribute | WebComPyApp (immutable) | RenderContext (per-request) |
|---|---|---|
| `_config` | ✓ | |
| `_root_component_def` | ✓ | |
| `_router_pages`, `_router_mode`, `_router_base_url` | ✓ (definitions) | |
| `_plugin_classes` | ✓ (discovered classes) | |
| `_component_generators` | ✓ (registered generators) | |
| `_profile` | ✓ (config-derived, never mutated) | |
| `_di_scope` | | ✓ (new per request) |
| `_component_store` | | ✓ (new per request, definitions populated from `_component_generators` via `_register_deferred_components()`) |
| `_router` | | ✓ (new per request) |
| `_root` | | ✓ (new per request) |
| `_defer_depth` | | ✓ |
| `_deferred_callbacks` | | ✓ |
| `_profile_data` | | ✓ (per-request, forwarded from `WebComPyApp.profile_data` in browser) |
| `_hydrate` | ✓ (config-derived, never mutated per request — hydration flag comes from AppConfig) | |

**Design principle**: When uncertain whether a new element belongs to `WebComPyApp` or `RenderContext`, prefer `RenderContext`. This errs on the side of safety against cross-request vulnerabilities.

### Decision 3: Signal graph globals → `ContextVar`, `_epoch` stays global

**Choice**: Convert `_active_consumer` and `_in_notification_phase` in `_graph.py` from module-level globals to `ContextVar`s with module-level fallback globals (`_active_consumer_global`, `_in_notification_phase_global`) for PyScript environments where ContextVar propagation is unreliable across JS→Python callbacks. Keep `_epoch` as a module-level global that is **never reset** — it grows monotonically and serves as a logical clock for staleness detection. Remove `reset_graph_state()` entirely; disposal of signal nodes is handled by `consumer_destroy()` called from DI scope and effect scope disposal.

**Alternatives considered**:
- **Reset `_epoch` per RenderContext**: Rejected because it creates a race condition during concurrent requests. Request A's signal nodes have `last_clean_epoch=5`, Request B's `dispose()` resets `_epoch=0`, then Request A's nodes are incorrectly treated as stale (`0 != 5`). Monotonic growth is safe.
- **Reset `_epoch` at dispose but sequence is non-concurrent**: Rejected because Starlette+uvicorn uses `asyncio` which is concurrent within a single event loop.
- **Keep all as globals**: Rejected because `_active_consumer` and `_in_notification_phase` are set/reset during computation and could interleave across async tasks without ContextVar isolation.

**Rationale**: `ContextVar` provides per-async-task isolation for `_active_consumer` and `_in_notification_phase`, which are transient computation state. The fallback globals exist for PyScript where ContextVar bindings are lost across JS→Python callbacks (same pattern already used for `_active_di_scope`/`_app_di_scope`). `_epoch` is a monotonically increasing logical clock — since each `RenderContext` creates all-new signal nodes, their `last_clean_epoch` is always set to the current `_epoch` at creation time, which is correct regardless of the epoch's absolute value. Python ints have unlimited precision, so overflow is not a concern.

### Decision 4: Plugin lifecycle hooks

**Choice**: Add `on_render_context_init(ctx: RenderContext)` hook and change `on_app_ready(app: WebComPyApp)` to `on_app_ready(ctx: RenderContext)`.

**Rationale**: Plugins need per-request lifecycle hooks for use cases like:
- Injecting request-scoped DI providers (authentication context, request IDs)
- Setting up per-request logging/tracing

The distinction between hooks:
- `on_app_init(app: WebComPyApp)`: Called once during app definition setup. Immutable setup only (no DI access).
- `on_render_context_init(ctx: RenderContext)`: Called per request (server) or once (browser). DI providers can be registered here.
- `on_app_ready(ctx: RenderContext)`: Called only in the browser after DOM is available. Browser-specific initialization.

This is a **breaking change** for `on_app_ready` signature. Plugins must change `on_app_ready(self, app)` to `on_app_ready(self, ctx)`. No backward compatibility is maintained (WebComPy is pre-stable software).

### Decision 5: `app.run()` delegates to `RenderContext` internally

**Choice**: `app.run()` in the browser creates a single `RenderContext` internally and delegates to it. The user-facing API remains unchanged.

**Rationale**: Browser behavior is already correct (one app, one rendering context, single user). Wrapping it in `RenderContext` unifies the rendering path and ensures the same code handles both environments, just with different `RenderContext` lifecycles.

### Decision 6: `RenderContext.dispose()` for cleanup

**Choice**: `RenderContext` has a `dispose()` method that cleans up all request-scoped resources: DI scope child disposal, EffectScope disposal, Signal graph state reset, and removal of DOM references.

**Rationale**: Without explicit disposal, Python's GC would eventually collect `RenderContext` objects, but the Signal graph's bidirectional references (producer-consumer edges) can prevent garbage collection. Explicit disposal ensures deterministic resource cleanup, preventing memory leaks on the server.

### Decision 7: `WebComPyApp.__init__` restructuring

**Choice**: `WebComPyApp.__init__` performs discovery (plugin discovery, component registration) and stores immutable definitions. It does NOT create a `DIScope`, `Router` instance, or `AppDocumentRoot`. Instead, `create_render_context()` handles full initialization including DI scope creation, port injection, component tree construction, and plugin initialization.

**Migration**: The browser path `app.run()` calls `self.create_render_context()` internally. The server path calls `app.create_render_context(path)` explicitly per request.

## Risks / Trade-offs

- **[Breaking change: `on_app_ready` signature]** → No backward compatibility. Plugins must update. WebComPy is pre-stable software, breaking API changes are acceptable.
- **[Performance cost of per-request RenderContext creation]** → The most expensive operation (component tree construction) already happens per-request in the current SSR path via `app.set_path()` + `app._root.render()`. Creating a fresh `RenderContext` adds only cheap operations (DIScope, ports, Router). Benchmark before/after to confirm negligible overhead.
- **[Signal graph `_epoch` as global]** → Keep as monotonically increasing global (never reset). Each fresh RenderContext creates new signal nodes whose `last_clean_epoch` receives the current `_epoch` value at construction, which is always correct for staleness detection. Resetting `_epoch` would cause cross-request staleness bugs during concurrent SSR.
- **[Plugin migration burden]** → Provide clear migration guide. The change is small (one parameter type change). Most plugins don't use `on_app_ready` at all.