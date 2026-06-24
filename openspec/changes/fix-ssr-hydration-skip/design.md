# Design: SSR/SSG Hydration Skip

## Problem

`AppDocumentRoot._render()` calls `child._hydrate_node()` when `self._app._hydrate` is `True`. `DynamicElement._hydrate_node()` recursively walks the children and for each non-mounted child calls `asyncio.ensure_future(child._render())`. These fire-and-forget tasks are not awaited in the current coroutine, so `AppDocumentRoot._render()` returns to `await generate_html(...)` while the tasks are still pending.

In a browser event loop the tasks eventually complete. In SSR/SSG, `ctx.dispose()` runs immediately after `await generate_html` returns, marking the DI scope as disposed. The still-pending tasks then run, call `Component.__init__` → `__setup` → `inject(_HEAD_PROPS_KEY)`, and the injection fails because the DI scope is disposed. The user sees empty routed content (e.g. `<div webcompy-component="HomePage"></div>` with no children).

## Decisions

### Decision 1: Force `app._hydrate = False` in non-pyscript environments

**Chosen**: In `WebComPyApp.__init__`, compute `self._hydrate = self._config.hydrate and ENVIRONMENT == "pyscript"`.

**Rationale**: Hydration is a browser concept — adopting prerendered DOM nodes in the JS runtime. The server is **producing** the prerendered content, not adopting it. Forcing `_hydrate = False` server-side short-circuits the existing `if self._app and self._app._hydrate and not self.__hydrated:` guard in `AppDocumentRoot._render()` so the synchronous `for child in self._children: await child._render()` path is taken exclusively. This guarantees a complete await-chain render.

**Rejected alternatives**:
- *Apply the `ENVIRONMENT` check inside `AppDocumentRoot._render()`* — bakes environment knowledge into the root component, mixing layers. The current `WebComPyApp` initialization is the single boundary between user config and runtime behavior, so this is the right place to apply the override.
- *Make `_hydrate_node` environment-aware internally* — duplicates the env check across all `DynamicElement` subclasses. Higher coupling, lower clarity.
- *Wait for `feat/ssg-via-ssr` to fix this* — `feat/ssg-via-ssr` is a CLI integration that shares the ASGI app; it does not modify the fire-and-forget behavior. The bug would still exist after unification, and a follow-up fix would still be needed.

### Decision 2: Document user-visible behavior in spec, not in error message

**Chosen**: Add a `#### Scenario` block to `app-config` and `app-lifecycle` specs stating that `hydrate` is effective only in the `pyscript` environment. Do not add a runtime warning.

**Rationale**: The `ENVIRONMENT` constant is set once at process start and is never ambiguous; printing a warning would be noise. Spec documentation is the right place because users configuring `hydrate=True` (or accepting the default) need to understand its scope.

## Implementation

The change is a single-line update to `webcompy/app/_app.py`:

```python
# Before
self._hydrate = self._config.hydrate

# After
self._hydrate = self._config.hydrate and ENVIRONMENT == "pyscript"
```

The existing `if self._app and self._app._hydrate and not self.__hydrated:` guard in `AppDocumentRoot._render()` is unchanged. In non-pyscript environments the guard evaluates `False` and the await chain renders the subtree synchronously.

No changes to:
- `webcompy/app/_root_component.py`
- `webcompy/elements/types/_dynamic.py`
- `webcompy/elements/types/_base.py`
- `webcompy/elements/types/_abstract.py`
- The browser-side render path (`app.run()`)

## Future refactor opportunities (deferred)

The fire-and-forget `asyncio.ensure_future(child._render())` in `DynamicElement._hydrate_node()` is a code smell that warrants a broader refactor. Two alternatives were considered during the design phase:

### Option B — DOM port abstraction (deferred)

Move the hydration responsibility into the DOM port layer:
- `BrowserDOMPort._init_node` adopts the existing prerendered node when one is found; `ServerDOMPort._init_node` always creates a fresh node.
- `_hydrate_node()` and its `asyncio.ensure_future` call are removed entirely.
- The `_pending_render_tasks` bookkeeping moves out of `DynamicElement`.

This is a larger change that touches `port-abstraction`, `elements`, `element-preserve-children`, and `app-lifecycle` specs. Worth pursuing as a follow-up if the framework grows more SSR-style features.

### Option C — Render scheduler port (deferred)

Introduce a `RenderSchedulerPort` (browser: `asyncio.ensure_future`; server: synchronous — the coroutine is returned to the caller and awaited there). `DynamicElement._hydrate_node()` would call `inject(RENDER_SCHEDULER_PORT_KEY).schedule(child._render())`. Centralizes the only `ensure_future` call site behind a port.

This is a mid-sized change and adds one new port abstraction. Worth pursuing if the `ensure_future` pattern spreads to other call sites.

This change takes the minimum-impact route to unblock the SSR/SSG output defect. The refactor opportunities remain available for a future change without conflict.
