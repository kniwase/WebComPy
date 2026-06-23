# Proposal: Async Rendering Pipeline

## Why

The current rendering pipeline is entirely synchronous: `ElementAbstract._render()`, `ElementWithChildren._render()`, `Component._render()`, `AppDocumentRoot._render()`, `SwitchElement._refresh()`, `RepeatElement._refresh()`, `generate_html()`, and `Component.__setup()` are all synchronous. This prevents:

1. **Async component definitions** — Developers cannot use `async def` setup functions (e.g., for async data fetching during setup).
2. **Async lifecycle hooks** — `on_before_rendering` and `on_after_rendering` must be synchronous, blocking async I/O patterns.
3. **Sibling parallelism** — Children in `ElementWithChildren._render()` are rendered sequentially, with no opportunity for concurrent I/O or computation.
4. **Future async SSR** — Server-side rendering with async data fetching (e.g., per-route API calls during SSG) requires the pipeline itself to be async.

This change converts the entire rendering pipeline from synchronous to async, enabling async lifecycle hooks — while maintaining full backward compatibility with existing sync code. Async component definitions and sibling parallel rendering are out of scope for this change and will be addressed in follow-up changes.

## What Changes

- **`ElementAbstract._render()` → `async def _render(self):`** — Base render method becomes async; calls `self._mount_node()` synchronously (not awaited) within the async method.
- **`ElementWithChildren._render()` → `async def _render(self):`** — Uses sequential `await` iteration for child rendering.
- **`DynamicElement._render()` → `async def _render(self):`** — Async render for `SwitchElement`/`RepeatElement`.
- **`SwitchElement._refresh()` → `async def _refresh(self, *args):`** — Async refresh with deferred after-rendering callbacks.
- **`RepeatElement._refresh()` → `async def _refresh(self, *args):`** — Async refresh for list reconciliation.
- **`Component._render()` → `async def _render(self):`** — Awaits async lifecycle hooks and parent render.
- **`on_before_rendering`/`on_after_rendering` → async-aware** — Detects async callables via `inspect.iscoroutinefunction()` and awaits them.
- **`ComponentProperty` type update** — `on_before_rendering` and `on_after_rendering` fields typed as `Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]`.
- **`Context.on_before_rendering()`/`Context.on_after_rendering()`** — Accept both sync and async callables.
- **`AppDocumentRoot._render()` → `async def _render(self):`** — Async render with DI scope management.
- **`generate_html()` → `async def generate_html(...)`** — Returns `Awaitable[str]`.
- **`app.run()` uses `resolve_async`** — Browser entry point schedules async render.
- **`_aio_run_browser()` / `_aio_run_server()`** — Updated to support async rendering.

## Capabilities

### New Capabilities

- `async-rendering`: The rendering pipeline supports async lifecycle hooks. Existing sync components and hooks continue to work without modification.

### Modified Capabilities

- `components`: Lifecycle hooks (`on_before_rendering`, `on_after_rendering`) may be async callables.
- `app-lifecycle`: `app.run()` schedules the async render via `resolve_async`. `generate_html()` is now async and must be awaited.
- `architecture`: The rendering pipeline is async in both environments, enabling future async SSR patterns.

## Known Issues Addressed

- **No async component definitions** — Currently `@define_component async def MyComponent(context): ...` silently ignores the coroutine return. This change lays the groundwork but does not implement async component definitions (tracked in `feat/async-component-setup`).
- **No async lifecycle hooks** — Currently `@on_after_rendering async def hook(): ...` silently ignores the coroutine. After this change, async hooks are awaited.

## Non-goals

- **Async component definitions** — `async def` component setup functions are not supported in this change. They will be implemented in `feat/async-component-setup`.
- Per-route async data fetching during SSG (separate change: `feat/ssg-via-ssr`).
- Changing the signal system to be async-aware.
- Changing `ElementWithChildren._render()` to use `asyncio.gather()` for sibling parallelism (the current sequential behavior is preserved for correctness and will be addressed in a follow-up change).
- Modifying the `TestRenderer` or testing module (the testing module will need a separate update to support async rendering).
- Making `_mount_node()` async (it remains synchronous — only `_render()` becomes async).

## Dependency

- This is the **foundational change** for the `feat/async-ssr-pipeline` branch. The following changes depend on this one: `feat/async-component-setup`, `feat/server-fetch-port-asgi`, `feat/ssg-via-ssr`, `feat/client-only-component`, `feat/suspense-component`, `feat/hydration-data-transfer`.

## Impact

- **Affected modules**: `webcompy/elements/types/` (all element type modules), `webcompy/components/` (component, hooks, libs), `webcompy/app/` (root component, app), `webcompy/cli/` (html, generate, server), `webcompy/aio/` (async utilities)
- **Breaking**: `generate_html()` changes from sync to async — internal function in `webcompy/cli/_html.py` with no public consumers. Only callers to update are `webcompy/cli/_generate.py` and `webcompy/cli/_server.py`. All public-facing entry points (`webcompy start`, `webcompy generate`, `create_asgi_app()`) remain callable as documented.
- **Backward compatible**: Sync component definitions and lifecycle hooks continue to work without modification. The `inspect.iscoroutinefunction()` check transparently handles both sync and async callables.