# Design: Async Component Setup

## Problem

`Component.__init__()` calls `__setup()` which executes the component definition function. If the definition is `async def`, calling it returns a coroutine, not a template. Python's `__init__` cannot be `async`, so we cannot `await` the coroutine during construction. A two-phase init strategy is needed: store the coroutine at init time, resolve it during the first async `_render()`.

## Decisions

### Decision 1: Two-phase initialization

**Chosen**: `Component.__init__()` detects async definitions and defers `__init_component()` to `_render()`.

**Phase 1 — `__init__`**:
```python
def __init__(self, component_def, props, slots):
    self._instance_id = uuid4()
    self._attrs = {}
    self._event_handlers = {}
    self._ref = None
    self._children = []
    self._head_props = None
    self._pending_async_template = None
    super().__init__()
    property = self.__setup(component_def, props, slots)
    if self._pending_async_template is None:
        self.__init_component(property)
```

**Phase 2 — `_render()`**:
```python
async def _render(self):
    if self._pending_async_template is not None:
        template = await self._pending_async_template
        self._pending_async_template = None
        property = self._property
        property["template"] = template
        self.__init_component(property)
    # ... normal async render flow ...
```

**Rationale**: This is the only viable pattern — `__init__` cannot await. The two-phase pattern is well established (e.g., `__init__` + `__await__` in asyncio-friendly classes, or lazy initialization). Since `_render()` is already async (from `feat/async-rendering-pipeline`), awaiting the coroutine there is natural.

**Rejected alternative**: Using `asyncio.run()` in `__init__` — this would create a new event loop on the server and fail in the browser where PyScript manages the loop.

### Decision 2: Detection via `inspect.iscoroutinefunction()`

**Chosen**: In `__setup__()`, check `inspect.iscoroutinefunction(component_def)` before calling it. If true, call it to get the coroutine, store in `self._pending_async_template`, set `template = None`. If false, call it and use the result directly.

```python
try:
    if iscoroutinefunction(component_def):
        coro = component_def(context)
        self._pending_async_template = coro
        template = None
    else:
        template = component_def(context)
finally:
    # ... existing context/di resets ...
```

**Rationale**: Checking the function type before calling it avoids needing to inspect the return value. `iscoroutinefunction()` is a well-known Python stdlib function in `inspect`. The alternative — calling the function and checking `inspect.iscoroutine(result)` — would also work but is less explicit.

### Decision 3: `ComponentProperty` template becomes nullable

**Chosen**: `ComponentProperty["template"]` type changes from `ElementChildren` to `ElementChildren | None`. When None, the component is in the unresolved async state.

**Rationale**: The template field holds `None` between `__init__` and the first `_render()` for async components. This accurately reflects the state. The `Component._render()` method resolves and replaces it before `__init_component()` is called, so no other code sees the `None` value.

### Decision 4: `FuncComponentDef` type alias broadened

**Chosen**: The type alias expands to accept async callables:
```python
FuncComponentDef: TypeAlias = (
    Callable[[Context[Any]], ElementChildren]
    | Callable[[Context[Any]], Coroutine[Any, Any, ElementChildren]]
)
```

Same change in `_generator.py` for the `define_component` parameter type.

**Rationale**: This reflects the real possibility of async component definitions. The `_is_function_style_component_def()` guard already checks `callable()` and `__webcompy_component_definition__` attribute — it doesn't care about the return type, so it needs no change.

### Decision 5: No changes to `Component.__setup__()` hook/DI/scope logic

**Chosen**: The DI scope setup, effect scope creation, context management, and lifecycle hook extraction in `__setup__()` are unchanged. Only the `template = component_def(context)` line is wrapped in the async detection branch.

**Rationale**: All the context machinery (DI scope, effect scope, lifecycle hooks) works the same for async definitions — they're set up during `__init__` synchronously and cleaned up in the `finally` block. Only the template resolution is deferred.

## Interaction with signal-triggered refresh (e.g. `_refresh_sync`)

The foundational `feat/async-rendering-pipeline` change introduced a sync wrapper `_refresh_sync` on `RepeatElement`/`SwitchElement` that calls `loop.run_until_complete(self._refresh(*args))` to make signal-triggered refresh complete synchronously with the signal update. That is safe today because `_refresh` only awaits sync `_render()` of children (no user async I/O on the path).

**Concern**: Once async component definitions land, a dynamic element's subtree may contain components whose setup is `async def` (e.g. fetching data). When such a dynamic element is refreshed in response to a signal change, `_refresh_sync` → `loop.run_until_complete(self._refresh(...))` would block the running event loop until the user async operation completes. Worse, if the user async operation depends on a task already scheduled on the same event loop, the result is a deadlock. This is a latent risk introduced by combining the foundational `_refresh_sync` mechanism with async setup.

The foundational design Decision 13 records that `_refresh_sync` is intentionally registered only from `_render()` and `_refresh` (async fire-and-forget) from `_on_set_parent()`. That split does not by itself protect against the async-subtree case once async setup is in play, because both paths may end up running user async code.

### Decision 6: Two-tier refresh — sync structural patch, async content via Suspense

**Chosen**: Separate the synchronous structural work of `_refresh` from the asynchronous content resolution:

1. **Structural patch (sync)** — `_patch_children()` and `_position_element_nodes()` continue to run synchronously so that DOM ordering guarantees and dependent synchronous signal consumers (`Computed` → `_update_text`) see a consistent DOM when the signal update returns. This must not rely on awaited user code.
2. **Async content resolution (fire-and-forget)** — The `await child._render()` portion of `_refresh` that involves `async def` component setup is NOT executed inside `_refresh_sync`'s `run_until_complete`. Instead:
   - Child components whose `_pending_async_template is not None` are left in a placeholder state at the structural-patch step.
   - The enclosing `SuspenseElement` (from `feat/suspense-component`) owns the resolution of those coroutines via its own async `_render()` path (`asyncio.gather(*coroutines)`).
   - Until resolved, the Suspense shows its `fallback` in that slot. There is no event-loop block because the structural patch never awaits user I/O.

`_refresh_sync` is therefore only invoked on subtrees where all new children are sync. When a dynamic element is known to contain async components, the registration SHALL switch from `_refresh_sync` to the async `_refresh` (fire-and-forget) path, leaving resolution to the surrounding Suspense boundary.

**Rationale**: `asyncio.ensure_future` fire-and-forget in PyScript preserves the property that synchronous signal propagation completes before async tasks (the existing reason Decision 13 chose fire-and-forget for the `_on_set_parent` path). Routing async subtrees through Suspense reuses the async pipeline rather than forcing `run_until_complete` to block on user I/O.

**Rejected alternative**: Rip out `_refresh_sync` entirely and make every signal-triggered refresh fire-and-forget async. This requires rewriting every existing `test_switch_toggle`-style expectation to `await` the refresh, and breaks the documented "DOM update completes before the signal setter returns" contract that synchronous UIs depend on. Too invasive for this change; tracked as a possible future change.

### Decision 7: Async setup exception propagation

**Chosen**: When `await self._pending_async_template` raises inside `Component._render()`:

- The exception propagates up through the `await child._render()` chain in `ElementWithChildren._render()` / `DynamicElement._refresh()` exactly like any sync render exception (sequential short-circuit semantics, per the `async-rendering` spec requirement "Sibling children shall render sequentially" — scenario "One child raises during sibling rendering").
- The exception is NOT swallowed at the `Component` level. The closest enclosing `SuspenseElement` (from `feat/suspense-component`) SHALL catch the exception in its `_render()` and render `error_fallback` when provided. If no `SuspenseElement` encloses the failing component, the exception propagates to the root and is logged via the `resolve_async` `on_error` hook (default `_log_error`).
- `_pending_async_template` stays non-None; the component is left in the unresolved state. Its effect scope and DI scope were already closed in `__setup__`'s `finally` block (Decision 1's existing cleanup path), so there is no resource leak.

**Why this requires `SuspenseElement` cooperation**: The standard `ElementWithChildren._render()` loop has no general try/except — adding one would conflict with sequential short-circuit semantics. Suspense is the explicit boundary where the framework knows it is async-rendering a subtree and mayしたいに捕捉する. See the new `feat-suspense-component` Decision D9 for the catching mechanism.

## No changes to

- `_generator.py`'s `ComponentStore` — registration is name-based, not affected by async
- `_generator.py`'s scoped CSS logic — independent of template resolution
- `_hooks.py` — lifecycle decorators already accept any callable
- DI subsystem — scope creation/destruction is unchanged
- App/SSG/CLI layers — they already call async `_render()`

## Risks / Trade-offs

- **Uninitialized component window**: Between `__init__` and first `_render()`, the component's `_tag_name`, `_attrs`, and `_children` are uninitialized (inherited from `ElementBase` defaults). No code should query these before `_render()` completes, which is already the contract — `_render()` is always called before any DOM interaction.
- **Error during async setup**: If `await coro` in `_render()` raises, the component remains uninitialized. The exception propagates through the async `_render()` chain (see Decision 7). The effect scope and DI scope are already cleaned up (they were closed in `__setup__`'s `finally` block), so there's no resource leak. The component's element node may be partially mounted; the error handling responsibility lies with the enclosing `SuspenseElement` or, in its absence, the root render's `on_error` hook.
- **Event-loop block via `_refresh_sync`**: Even with Decision 6's two-tier split, `_refresh_sync` still uses `loop.run_until_complete` on subtrees that callers believe are sync. There is no runtime guard against a sync-tagged dynamic element later containing async children (e.g. via a passed-in component generator). Mitigation: the registration logic in `RepeatElement._render()` / `SwitchElement._render()` SHALL re-check the subtree type and fall back to the async `_refresh` path when async children are detected. This check is part of this change's task list.
