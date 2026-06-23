# Design: Async Rendering Pipeline

## Context

The rendering pipeline in WebComPy is currently synchronous from top to bottom. The call chain is:

```
app.run() → AppDocumentRoot._render() → Component._render() → ElementWithChildren._render() → ... → ElementAbstract._render() → _mount_node()
```

On the server side, `generate_html()` calls `_HtmlElement.render_html()` which calls `self._render()`. On the browser side, `app.run()` calls `self._root.render()` (which is `self._root._render`).

This synchronous design prevents:
1. Async component setup functions (e.g., `@define_component async def MyComponent(context): ...`)
2. Async lifecycle hooks (`on_before_rendering`, `on_after_rendering`)
3. Async child rendering (awaiting `child._render()` mid-tree)
4. Future async SSR capabilities (per-route data fetching, streaming)

## Goals / Non-Goals

**Goals:**
- Convert the entire rendering pipeline to async
- Support async component definitions transparently (sync still works)
- Support async lifecycle hooks transparently (sync still works)
- Render sibling children sequentially via `for child in self._children: await child._render()` (matches pre-async behavior)
- Make `generate_html()` async
- Update `app.run()` to schedule async render
- Maintain full backward compatibility with existing sync code

**Non-Goals:**
- Per-route async data fetching during SSG (separate change)
- Changing the signal system to be async-aware
- Making `_mount_node()` async (it remains sync — only DOM operations)
- Sibling parallel rendering via `asyncio.gather()` (deferred to future work; see "Future Work" section in spec)

## Decisions

### Decision 1: `_render()` becomes `async def _render(self)`

**Chosen**: Change `ElementAbstract._render()` from `def _render(self):` to `async def _render(self):`. All overrides in `ElementWithChildren`, `DynamicElement`, `RepeatElement`, `SwitchElement`, `Component`, and `AppDocumentRoot` also become async.

**Rationale**: This is the foundational change. Making `_render()` async allows every render step to `await` async operations (component setup, lifecycle hooks, child rendering). The alternative — keeping `_render()` sync and wrapping async calls with `asyncio.run()` at each call site — would break the event loop in both Emscripten (where the PyScript runtime manages the loop) and CPython (where `asyncio.run()` creates a new loop).

**Key change**: The base method signature changes from `def _render(self):` to `async def _render(self):`. This propagates to every subclass. `_mount_node()` remains synchronous and is NOT awaited — async leaf elements call `_mount_node()` directly within their `async def _render(self)` with no `await` points.

### Decision 2: `ElementWithChildren._render()` renders siblings sequentially

**Chosen**: Change `ElementWithChildren._render()` to:

```python
async def _render(self):
    await super()._render()
    for c_idx, child in enumerate(self._children):
        child._node_idx = self._node_idx + c_idx
        await child._render()
    if (node := self._get_node()) is not None:
        for _ in range(node.childNodes.length - self._children_length):
            node.childNodes[-1].remove()
```

**Rationale**: Sequential rendering via `for child in children: await child._render()` preserves the exact DOM ordering guarantees of the pre-async pipeline. Each child is fully rendered before the next begins, ensuring deterministic DOM state. This avoids race conditions that can occur when multiple coroutines manipulate the DOM concurrently.

In the browser (PyScript), there is no true parallelism anyway — all DOM operations happen on the main thread. The structural benefit of `asyncio.gather()` (concurrent coroutine scheduling) does not translate to actual performance gain for DOM-bound rendering. Sequential rendering is simpler, safer, and behaviorally identical to the sync pipeline.

**Trade-off**: I/O-bound parallelism during SSG is not exploited. For example, if two sibling components both fetch data during `on_before_rendering`, they cannot fetch concurrently. This is a deliberate limitation for this change. Future work may introduce `asyncio.gather()` with proper DOM ordering guarantees, atomic cleanup, and ContextVar isolation.

### Decision 3: Async component definitions deferred to separate change

**Chosen**: `Component.__setup()` remains synchronous. Async component definitions (`async def MyComponent(context): ...`) are NOT supported in this change. They will be implemented in `feat/async-component-setup`.

**Rationale**: `Component.__init__()` calls `__setup()`, and `__init__` cannot be `async` in Python. Resolving async component definitions requires a two-phase init pattern (store the coroutine, await it during `_render()`) that touches the component initialization model deeply. Separating this concern keeps the foundational change focused and reduces risk.

This change delivers:
1. Making `_render()` async across the entire pipeline
2. Supporting async lifecycle hooks
3. Making `generate_html()` async

### Decision 4: Async lifecycle hooks via `inspect.iscoroutinefunction()`

**Chosen**: In `Component._render()`, detect async lifecycle hooks and await them:

```python
async def _render(self):
    on_before_rendering = self._property["on_before_rendering"]
    if iscoroutinefunction(on_before_rendering):
        await on_before_rendering()
    else:
        on_before_rendering()
    await super()._render()
    on_after_rendering = self._property["on_after_rendering"]
    render_ctx = _active_app_context.get()
    if render_ctx is not None and render_ctx._defer_depth > 0:
        render_ctx._deferred_callbacks.append(on_after_rendering)
    else:
        if iscoroutinefunction(on_after_rendering):
            await on_after_rendering()
        else:
            on_after_rendering()
```

**Rationale**: `inspect.iscoroutinefunction()` cleanly detects async hooks. This is backward compatible — sync hooks work unchanged. The deferred callback mechanism for `on_after_rendering` (used during `SwitchElement._refresh()`) is preserved.

**Deferred async hooks**: When an async `on_after_rendering` hook is deferred (via `start_defer_after_rendering()`), it is scheduled via `inject(HOST_PORT_KEY).schedule_macro_task()` which already handles async callables (the `schedule_macro_task` method on `HostPort` receives a callback and schedules it). Async deferred hooks are wrapped in `aio_run()` to handle the coroutine.

### Decision 5: `AppDocumentRoot._render()` becomes async

**Chosen** (pseudo-code showing the pattern):

```python
async def _render(self):
    token = _active_di_scope.set(self._di_scope)
    render_ctx_token = _active_app_context.set(self._render_context) if self._render_context else None
    try:
        on_before = self._property["on_before_rendering"]
        if iscoroutinefunction(on_before):
            await on_before()
        else:
            on_before()
        self._mount_node()
        if self._app and self._app._hydrate and not self.__hydrated:
            self.__hydrated = True
            for child in self._children:
                await child._hydrate_node()
        for child in self._children:
            await child._render()
        on_after = self._property["on_after_rendering"]
        if iscoroutinefunction(on_after):
            await on_after()
        else:
            on_after()
        # ... rest (profile, loading removal, etc.) ...
    finally:
        if ENVIRONMENT != "pyscript":
            if render_ctx_token is not None:
                _active_app_context.reset(render_ctx_token)
            _active_di_scope.reset(token)
```

**Rationale**: `AppDocumentRoot._render()` is the top of the render tree. Making it async and using sequential child rendering enables future async SSR (per-route data fetching, streaming) and async lifecycle hooks. The DI scope and app context management are preserved. Sibling parallel rendering is intentionally NOT enabled in this change — it is deferred to future work and requires the prereqs listed in the spec's "Future Work" section (DOM ordering, atomic cleanup, ContextVar isolation).

**Critical**: The `_hydrate_node()` call MUST remain inside the `if self._app and self._app._hydrate` guard block. Moving it outside (unconditionally calling `_hydrate_node()` on every render) causes duplicate DOM nodes because:
1. In non-hydrate mode, `_hydrate_node()` creates floating `_node_cache` entries that are never attached to the DOM
2. These orphan nodes still register signal callbacks (attribute updaters, text updaters)
3. On signal change, callbacks fire on orphan nodes with `parentNode=None`, producing incorrect output (e.g., `_update_text` on a detached text node)
4. The real render pass creates properly attached nodes, but the orphan nodes' callbacks race with the real nodes'

This bug is a regression from the async conversion — the original code correctly guarded `_hydrate_node()` inside the `if self._app._hydrate` block. The async conversion inadvertently moved the `for child in self._children: await child._hydrate_node()` call outside the if block.

### Decision 6: `generate_html()` becomes async

**Chosen**: `generate_html()` becomes `async def generate_html(...) -> str:`. Callers must `await` it.

```python
async def generate_html(app, app_package_name, dev_mode, prerender, app_version, wheel_filename, ...) -> str:
    # ... same logic, but _HtmlElement.render_html() becomes async ...
    html = await root_element.render_html()
    # ... return html ...
```

And `_HtmlElement.render_html()` becomes async:

```python
async def render_html(self):
    port = inject(DOM_PORT_KEY)
    root_node = port.create_element("div")
    root_node.__webcompy_node__ = False
    root_node.__webcompy_prerendered_node__ = True
    self._parent = cast("ElementWithChildren", _DummyParent(root_node))
    self._node_idx = 0
    self._clear_node_cache()
    await self._render()
    # ... rest ...
```

**Rationale**: Since `_render()` is now async, `render_html()` must await it. This propagates to `generate_html()` which must also be async. Callers in `_generate.py` and `_server.py` must use `await generate_html(...)`.

**Server-side impact**: In `_server.py`, the `send_html` handler is already an `async def` (Starlette ASGI), so awaiting `generate_html()` is natural. In `_generate.py`, `generate_static_site()` must be made async or use `asyncio.run()` to call `await generate_html()`.

### Decision 7: `app.run()` schedules async render

**Chosen**: In browser environment, `app.run()` uses `asyncio.ensure_future()` to schedule the async render:

```python
def run(self) -> None:
    if ENVIRONMENT != "pyscript":
        raise WebComPyException("app.run() can only be called in a browser environment.")
    self._record_phase("run_start")
    self._plugin_manager.call_on_app_ready(self)
    self._root._selector = self._config.selector
    asyncio.ensure_future(self._root._render())
```

**Rationale**: In the browser (PyScript), the event loop is already running. `asyncio.ensure_future()` schedules the async render as a task on the existing loop. This is the standard pattern for starting async work from synchronous code in an already-running event loop.

### Decision 8: `_dispatch()` with async flag and environment-free signal layer

**Chosen**: Three changes that work together to eliminate `_make_signal_callback()` while keeping the signal layer (`webcompy/signal/`) completely free of environment awareness:

1. **`_on_marked_dirty` → `_dispatch`**: Renamed to reflect what it does (dispatch the callback), not what triggered it (being marked dirty).

2. **Async detection in `__init__`**: `iscoroutinefunction(self._callback)` evaluated once at construction time; stored as `_is_async: bool` flag. No runtime check needed in `_dispatch()`.

3. **ENVIRONMENT branch delegated to `_aio.py`**: `_dispatch()` does NOT reference `ENVIRONMENT`. Instead it calls into `_aio.py` via a new function `_resolve_async_callback(callback, value)` which encapsulates all environment-specific behavior (fire-and-forget in browser, synchronous execution in server/test).

**Implementation**:

```python
# webcompy/aio/_aio.py — new function
def _resolve_async_callback(callback: Callable[..., Any], value: Any) -> None:
    async def _safe():
        try:
            await callback(value)
        except Exception as err:
            _log_error(err)

    if ENVIRONMENT == "pyscript":
        aio_run(_safe())
    else:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_safe())
        else:
            import nest_asyncio
            if not getattr(loop, "_nest_asyncio_patched", False):
                nest_asyncio.apply(loop)
                loop._nest_asyncio_patched = True
            loop.run_until_complete(_safe())
```

```python
# webcompy/signal/_base.py — CallbackConsumerNode
class CallbackConsumerNode(SignalNode, _CallbackMixin):
    _callback: Callable[[Any], Any]
    _is_before: bool
    _is_async: bool
    _producer: SignalNode

    def __init__(self, callback, producer, is_before=False):
        super().__init__()
        self._callback = callback
        self._is_before = is_before
        self._is_async = iscoroutinefunction(callback)
        self._producer = producer
        self.consumer_is_always_live = True
        producer_add_live_consumer(producer, self)

    def _dispatch(self) -> None:
        if self._is_before:
            return
        from webcompy.signal._computed import Computed
        old_version = self._producer.version
        producer_update_value_version(self._producer)
        self.dirty = False
        if isinstance(self._producer, Computed) and self._producer.version <= old_version:
            return
        if self._is_async:
            from webcompy.aio._aio import _resolve_async_callback
            _resolve_async_callback(self._callback, self._producer._value)
        else:
            self._callback(self._producer._value)
```

The `ENVIRONMENT` import is removed from `webcompy/signal/_base.py`.

**What this replaces**: The `_make_signal_callback()` wrapper is removed. `RepeatElement._refresh` and `SwitchElement._refresh` register directly as `self._sequence.on_after_updating(self._refresh)` (no wrapper). All environment-specific behavior lives in `_aio.py`. The signal layer has zero awareness of browser vs server.

### Decision 9: `DynamicElement._render()` becomes async

**Chosen**:

```python
async def _render(self):
    parent_node = self._parent._get_node()
    for c_idx, child in enumerate(self._children):
        child._node_idx = self._node_idx + c_idx
        if child._mounted is None:
            await child._render()
    _position_element_nodes(self, parent_node, self._node_idx)
```

**Rationale**: `DynamicElement._render()` calls `child._render()` which is now async. The sequential rendering within `DynamicElement` (assigning `_node_idx` before rendering) is preserved.

The same `_position_element_nodes` call SHALL also be present in `SwitchElement._refresh()` after rendering new children (following `_patch_children()`, deferred callback execution, and child rendering). This ensures that after a switch case change, all child DOM nodes are repositioned at the correct index in the parent, preventing DOM ordering inconsistencies that can arise when `_patch_children()` removes/replaces some children without repositioning the remaining ones.

### Decision 10: `ComponentProperty` type update

**Chosen**: Update `ComponentProperty` TypedDict to accept both sync and async lifecycle hooks:

```python
class ComponentProperty(TypedDict):
    component_id: str
    component_name: str
    template: ElementChildren
    on_before_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    on_after_rendering: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
    on_before_destroy: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]
```

And `Context.on_before_rendering()` and `Context.on_after_rendering()` accept async callables:

```python
def on_before_rendering(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
    self.__on_before_rendering = func

def on_after_rendering(self, func: Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]) -> None:
    self.__on_after_rendering = func
```

**Rationale**: This is a type-only change. The runtime behavior is handled by `iscoroutinefunction()` checks in `_render()`. The `on_before_destroy` hook is also updated for consistency, though it's not called during async rendering (it's called during synchronous destruction).

### Decision 11: `generate_static_site()` and `create_asgi_app()` updates

**Chosen**:
- `generate_static_site()` becomes `async def generate_static_site(...)` and uses `await generate_html(...)` internally.
- In `_server.py`, the `send_html` handler already uses `async def` (Starlette), so it can `await generate_html(...)` naturally.
- The CLI entry point (`python -m webcompy generate`) calls `asyncio.run(generate_static_site(...))`.

**Rationale**: Since `generate_html()` is now async, all callers must await it. The CLI entry point wraps the call in `asyncio.run()`. The dev server handler can await directly since it's already async.

### Decision 12: Test suite uses pytest-asyncio instead of asyncio.run()

**Chosen**:
- Add `pytest-asyncio` and `nest-asyncio` to dev dependencies in `pyproject.toml`
- `asyncio_mode` SHALL NOT be set in `pyproject.toml` (defaults to strict mode, requiring explicit `@pytest.mark.asyncio` on each async test)
- Convert all test functions that call async code to `async def`
- Replace all `asyncio.run()` calls in tests with `await`
- Add a `run_sync()` helper for test utilities that need sync interfaces (e.g., `TestRenderer.render()`, `render_app_html_sync()`)

**Rationale**: `pytest` creates and manages its own event loop for test execution. Calling `asyncio.run()` inside a test raises `RuntimeError: asyncio.run() cannot be called from a running event loop`. The solution is to use `pytest-asyncio`, which provides an event loop per test and allows `async def` test functions to use `await` directly.

**Implementation details**:

```python
# run_sync() helper for test utilities
import asyncio
import nest_asyncio
from typing import TypeVar

T = TypeVar("T")

def run_sync(coro) -> T:
    """Run a coroutine, handling nested event loops from pytest-asyncio."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        if not getattr(loop, "_nest_asyncio_patched", False):
            nest_asyncio.apply(loop)
            loop._nest_asyncio_patched = True
        return loop.run_until_complete(coro)
```

```python
# Updated TestRenderer.render() uses run_sync()
class TestRenderer:
    @staticmethod
    def render(component, **kwargs):
        async def _render_async():
            # ... existing async logic ...
            await instance._render()
            return TestRendererResult(...)
        
        return run_sync(_render_async())
```

```python
# Updated test function - async def instead of def
async def test_element_render():
    el = SomeElement()
    await el._render()  # No asyncio.run() needed
    assert el._mounted is not None
```

**Risks/Trade-offs**:
- All 69 `asyncio.run()` calls across 20 test files must be updated. This is a large but mechanical change.
- `pytest-asyncio` adds a dependency, but it's a standard testing tool for Python async code.
- The `run_sync()` helper must be carefully designed to avoid infinite recursion or event loop conflicts.

### Decision 13: Sync wrapper for signal-triggered dynamic element refresh (in _render() only)

**Problem**: `RepeatElement._refresh()` and `SwitchElement._refresh()` are `async def` methods. When registered as signal callbacks via `on_after_updating(_refresh)`, `CallbackConsumerNode._dispatch()` detects `_is_async = True` and delegates to `_resolve_async_callback()`. In the browser (PyScript), this uses `aio_run()` → `asyncio.ensure_future()`, which does not guarantee the refresh task executes before the caller's next synchronous statement.

For dynamic elements created via `_on_set_parent()` (during component construction), this fire-and-forget path is actually safe, because synchronous signal propagation (Computed re-evaluation → text element `_update_text`) completes before async callbacks are dispatched. The repeat element case (where fire-and-forget was problematic) is handled differently — see the trailing-child cleanup in Decision 15.

For dynamic element callbacks registered from `_render()`, the sync wrapper (`_refresh_sync`) is used. The `_render()` path is async itself, so using `_refresh_sync` as the signal callback ensures DOM updates complete synchronously after the initial render.

**Chosen**: 
- `_on_set_parent()` (runs during synchronous construction): register async `_refresh` directly. In browser, this goes through fire-and-forget (`aio_run()`); in server/test, through `_resolve_async_callback()` with `nest_asyncio` + `run_until_complete()`.
- `_render()` (runs in async context): register `_refresh_sync` (sync wrapper with `loop.run_until_complete()`). This path is a fallback — normally `_on_set_parent()` runs first and sets `_signal_activated = True`, preventing `_render()` from re-registering.

The `_refresh_sync` wrapper pattern:

```python
def _refresh_sync(self, *args: Any):
    import asyncio
    from webcompy.utils._environment import ENVIRONMENT

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(self._refresh(*args))
    else:
        if ENVIRONMENT != "pyscript":
            import nest_asyncio

            if not getattr(loop, "_nest_asyncio_patched", False):
                nest_asyncio.apply(loop)
                loop._nest_asyncio_patched = True  # type: ignore[attr-defined]
        loop.run_until_complete(self._refresh(*args))
```

The `_render()` method (which calls `_refresh` for the initial render path) continues to use `await self._refresh()` — it is already in an async context and the `await` is correct there.

**Rationale**:
- `_refresh_sync` is a sync method (`def`), so `iscoroutinefunction(_refresh_sync)` returns `False`. `_dispatch()` treats it as a sync callback and calls it directly (no `_resolve_async_callback`).
- `loop.run_until_complete()` works natively in PyScript/Pyodide without `nest_asyncio.apply()`. In CPython (server/test), `nest_asyncio.apply()` is conditionally applied to allow nested `run_until_complete()` from within a running event loop (pytest-asyncio).
- The initial render path (`_render` → `await _refresh()`) is unaffected — it was already correctly async.
- `_on_set_parent()` MUST NOT use `_refresh_sync`. Using `loop.run_until_complete()` from within synchronous signal propagation (`producer_notify_consumers` → `_dispatch`) in PyScript interferes with the synchronous callback chain (Computed → text element `_update_text`), preventing dependent callbacks from executing before the signal setter returns. This was confirmed empirically: switching `_on_set_parent()` from `_refresh` to `_refresh_sync` caused `test_switch_toggle` to fail on `main`-based code.

**Trade-off**: `_refresh_sync` uses `loop.run_until_complete()` which blocks the event loop. This is acceptable when registered from `_render()`. For `_on_set_parent()` (the common code path), the async fire-and-forget path is safe because synchronous signal propagation completes before async callbacks are dispatched — the SwitchElement DOM update does not need to complete synchronously for dependent DOM state (like `flag-state` computed text) to be correct.

### Decision 14: Strict `is None` check in `_get_node()` to prevent stale PyProxy triggers

**Problem**: `ElementAbstract._get_node()` used `if not self._node_cache:` to check whether to initialize a new DOM node. In PyScript, a `PyProxy` wrapping a valid DOM element may evaluate as falsy in a boolean context when the proxy is "stale" (e.g., its underlying element was detached from the DOM). This triggered `_init_node()`, which created a new detached DOM element (a "ghost") and replaced `_node_cache`. The original element remained in the DOM without a Python reference, making `_remove_element()` a no-op and causing orphaned DOM nodes.

**Chosen**: Change `if not self._node_cache:` to `if self._node_cache is None:` in `_get_node()`. This ensures only an actual `None` cache (explicitly cleared by `_clear_node_cache()` or initialization) triggers `_init_node()`. A falsy-but-not-None PyProxy is returned as-is.

**Rationale**: The `_node_cache` is explicitly set to `None` on initialization and cleared via `_clear_node_cache()`. It should never be a falsy non-None value. The strict identity check is both safer and more performant (no `__bool__` call on the proxy).

### Decision 15: Fallback orphaned child removal after reconcile

**Problem**: When `_remove_element()` fails to remove a DOM node (due to Decision 14's stale proxy issue), the orphaned child remains in the parent element after the reconcile completes. This causes DOM state inconsistency (e.g., 3 `<li>` elements in a `<ul>` that should have 1).

**Chosen**: After `_reconcile_children()` completes its removal loop, check the parent element's child count against the expected count (sum of `new_children`'s `_node_count` values) and remove any trailing children that exceed expectations:

```python
if parent_node and not newly_created:
    expected = sum(c._node_count for c in new_children)
    while parent_node.childNodes.length > expected:
        parent_node.childNodes[-1].remove()
```

This runs only when no newly created children exist (to avoid race conditions with pending renders).

**Rationale**: The trailing-child removal is a safety net. In normal operation, `_remove_element()` correctly removes DOM nodes and the cleanup is a no-op. When a stale proxy prevents removal, the cleanup ensures DOM consistency without relying on proxy health.

## Risks / Trade-offs

- **Breaking change for `generate_html()` callers**: All code that calls `generate_html()` must now `await` it. This affects `_generate.py` and `_server.py` but is limited to the CLI layer.
- **Sibling parallelism is NOT enabled in this change**: An earlier draft used `asyncio.gather(return_exceptions=True)` for sibling rendering, but this was found to violate the spec's "Sibling children shall render sequentially" requirement (DOM ordering, short-circuit semantics). Sibling `asyncio.gather()` is therefore deferred to future work, with the prereqs (DOM ordering guarantees, atomic cleanup, ContextVar isolation) tracked in the spec's "Future Work" section.
- **Signal callback adaptation**: `_on_marked_dirty` renamed to `_dispatch` with an `_is_async` flag set at construction time. For `RepeatElement` and `SwitchElement`, the signal callback is a sync wrapper (`_refresh_sync`) that runs the async `_refresh` inline via `loop.run_until_complete()`. This ensures signal-triggered DOM updates complete synchronously in the browser (PyScript's `asyncio.ensure_future` does not guarantee timely task execution for fire-and-forget callbacks). User-defined async callbacks still use the fire-and-forget path via `_resolve_async_callback()`.
- **`Component.__init__` remains synchronous**: Async component definitions are not supported in this change. The component setup function must return an `ElementChildren` synchronously. This is a deliberate scope limitation — async component definitions will be added in a follow-up change.
- **Test migration effort**: Converting 20 test files with 69 `asyncio.run()` calls to `await` is a mechanical but time-consuming task. Mistakes during conversion could introduce subtle test failures.

## Open Issues Discovered Post-Completion

These were surfaced while reviewing the foundational change against the dependent in-progress changes (`feat-async-component-setup`, `feat-suspense-component`). They do not invalidate the foundation but should be addressed by, or coordinated with, those dependent changes.

### Open Issue A: `nest_asyncio` duplicated across three call sites

The conditional `nest_asyncio.apply(loop)` + `loop._nest_asyncio_patched` monkey-patch pattern is duplicated in:

1. `webcompy/aio/_aio.py:_resolve_async_callback()` (server/test path)
2. `webcompy/elements/types/_switch.py:_refresh_sync`
3. `webcompy/elements/types/_repeat.py:_refresh_sync`

This is a DRY violation and uses `nest_asyncio` (originally a test escape hatch) as a permanent architectural element, with `type: ignore` monkey-patching of a private loop attribute.

**Recommended follow-up** (tracked as a task in a future change or `feat-async-component-setup`): extract a single helper `webcompy/aio/_aio.py:_run_in_active_loop(coro)` that encapsulates the "no loop → `asyncio.run`; running loop → conditional `nest_asyncio.apply` + `run_until_complete`" decision. Both `_refresh_sync` implementations and `_resolve_async_callback` should delegate to it. Longer-term, pytest-asyncio full adoption should eliminate the test-side nesting motivation; server SSR keeps the helper only because `generate_html` runs inside the ASGI event loop and is also called from `loop.run_until_complete` test utilities inside `run_sync`.

### Open Issue B: Hydration double-render risk between `_hydrate_node` and `await child._render()`

`DynamicElement._hydrate_node()` (sync) schedules `asyncio.ensure_future(child._render())` for unmounted children, attaching a done callback that logs exceptions. The parent (`AppDocumentRoot._render()` / enclosing `_render()`) then runs `for child in self._children: await child._render()`. The combination means a hydrated-but-unmounted child may have both a scheduled render task and an inline `await child._render()` in flight for the same element.

Today this is held stable by:
- The `if self._app and self._app._hydrate and not self.__hydrated:` guard in `AppDocumentRoot._render()` (Decision 5 / spec requirement "AppDocumentRoot._render() shall guard hydration behind the _hydrate flag").
- `_dynamic.py` setting `_hydrated = False` at the end of `_render()` so subsequent call into `_render()` re-renders rather than relies on the scheduled task.

The recent fix commits (`04f722a` "address Medium review findings — hydration double-render, node position asymmetry, callback leak" and `83db473` "revert _hydrate_node() async to sync, resolving E2E regression") indicate this area is still settling. The guard relies on subtle flag ordering.

**Recommended follow-up** (tracked by `feat-client-only-component` / `feat-suspense-component` or a dedicated consolidation change): introduce an explicit `_hydration_pending` flag set when `_hydrate_node` schedules a render task, checked at the top of `_render()` to short-circuit (cancel the scheduled task or skip the inline render). This replaces the flag-ordering coupling with a single explicit dedup point. Any change there requires re-running the `/reactive` and `/switch` E2E pages, which is what motivated the original `83db473` revert.

### Open Issue C: Root render error visibility

`app.run()` schedules the root render via `resolve_async(self._root._render())`. `resolve_async`'s default `on_error=_log_error` means a raised async exception IS logged (via `webcompy.logging.error` with a cleaned traceback) — it is not swallowed silently. However, no user-visible error boundary is rendered: a top-level async setup failure that is not wrapped in a `Suspense` boundary surfaces only in the browser console / server logs.

This is fine as a baseline ("uncaught errors are logged"), but the `feat-suspense-component` D9 design now relies on this default-log behavior for the "no enclosing Suspense" case. The contract that SHOULD be documented/spec'd is:

> When an async render exception propagates to the root without an enclosing `SuspenseElement` (or future equivalent error boundary), the framework SHALL log the exception via the `resolve_async` default `on_error` hook AND SHALL NOT crash the running event loop. Surfacing a user-visible fallback is left to the developer via `Suspense` with `error_fallback`.

Treat this not as a gap to fix here, but as a contract to **codify** in `async-rendering/spec.md` (next Open Issue D) and to make explicit in `feat-suspense-component` / `feat-async-component-setup` exceptions sections. A future enhancement may add a default root-level error boundary; it is out of scope for these changes.

### Open Issue D: Async vs sync callback execution semantics differ across environments

`_resolve_async_callback()` (and therefore `CallbackConsumerNode._dispatch` via the `_is_async` flag) executes async callbacks differently per environment:

- **Browser (PyScript)**: `aio_run()` → `asyncio.ensure_future()` (fire-and-forget). Async callbacks do NOT necessarily complete before the next synchronous statement after the signal setter returns. This is intentional for UI responsiveness.
- **Server / test (CPython)**: `nest_asyncio` + `loop.run_until_complete()` — async callbacks complete synchronously before the signal setter returns. This is intentional for SSG/SSR output determinism.

This divergence is a deliberate design choice (the foundation made it), but the contract is implicit. It should be made explicit in the `async-rendering` spec so dependent changes (`feat-suspense-component`, SSG / data transfer) reason against a written guarantee, not an emergent behavior. The added Requirement is in this change's `specs/async-rendering/spec.md` (see the "Async signal callbacks execute environment-dependently" requirement).