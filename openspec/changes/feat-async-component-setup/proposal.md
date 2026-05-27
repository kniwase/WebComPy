# Proposal: Async Component Setup

## Why

After `feat/async-rendering-pipeline`, the rendering pipeline is async: `_render()` is `async def`, lifecycle hooks support async, `generate_html()` is async, and children render in parallel via `asyncio.gather()`. However, `Component.__setup()` remains synchronous — component definitions must return `ElementChildren` synchronously. Python's `__init__` cannot be `async`, so resolving async component definitions requires a two-phase initialization strategy.

This change enables async component definitions:

```python
@define_component
async def MyComponent(context):
    data = await fetch("/api/data")
    return html.DIV({}, data)
```

The `await` in the setup function executes on the event loop during the async `_render()` phase, with the result available for the initial render — eliminating the need for `useAsyncResult` fire-and-forget patterns for server-side data fetching during SSG/SSR.

## What Changes

- **`Component.__setup()`** — Detects async component definitions via `inspect.iscoroutinefunction()`. For async definitions, stores the coroutine in `self._pending_async_template` instead of calling `self.__init_component()`.
- **`Component.__init__()`** — Guards `self.__init_component()` with a check for `self._pending_async_template`. Sync definitions are initialized immediately as before.
- **`Component._render()`** — Checks `self._pending_async_template` at the start. If set, `await`s the coroutine, resolves the template, calls `self.__init_component()`, then proceeds with normal rendering.
- **`FuncComponentDef` type** — Broadened to accept `Callable[[...], Coroutine[Any, Any, ElementChildren]]`.
- **`define_component` decorator** — Broadened to accept async callables.
- **`ComponentProperty` type** — `template` field broadened to `ElementChildren | None` for the unresolved state.

## Capabilities

### New Capabilities

- `async-component-setup`: Component setup functions may be `async def`. The coroutine is resolved during `_render()` on the event loop. Sync definitions continue to work unchanged.

### Modified Capabilities

- `components`: `Component.__setup()` detects async definitions and defers `__init_component()` to `_render()`.
- `async-rendering`: `Component._render()` resolves pending async templates before continuing with normal rendering.

## Dependencies

- **Depends on**: `feat/async-rendering-pipeline` — `Component._render()` must already be `async def` for this change to apply.

## Known Issues Addressed

None directly from the known issues list. This is a new capability.

## Non-goals

- No changes to the signal system
- No changes to the DI scope management
- No changes to `on_before_destroy` (it remains sync)
- No SSR-specific async data fetching mechanism (that's `feat/ssg-via-ssr` / `feat/hydration-data-transfer`)
- No `Suspense` component or loading state UI for async setup (separate change)

## Impact

- **Affected modules**: `webcompy/components/_component.py`, `webcompy/components/_libs.py`, `webcompy/components/_generator.py`
- **Backward compatible**: Sync component definitions work without modification. `inspect.iscoroutinefunction()` transparently detects async definitions and diverts to the two-phase init path.
- **No CLI or server changes**: The async pipeline is already in place. Async setup just integrates into it.
