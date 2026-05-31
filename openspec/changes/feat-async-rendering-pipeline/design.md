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
3. Sibling parallel rendering (children rendered concurrently via `asyncio.gather()`)
4. Future async SSR capabilities (per-route data fetching, streaming)

## Goals / Non-Goals

**Goals:**
- Convert the entire rendering pipeline to async
- Support async component definitions transparently (sync still works)
- Support async lifecycle hooks transparently (sync still works)
- Enable sibling parallel rendering via `asyncio.gather()`
- Make `generate_html()` async
- Update `app.run()` to schedule async render
- Maintain full backward compatibility with existing sync code

**Non-Goals:**
- Per-route async data fetching during SSG (separate change)
- Changing the signal system to be async-aware
- Making `_mount_node()` async (it remains sync — only DOM operations)

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
3. Sibling parallel rendering
4. Making `generate_html()` async

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

**Rationale**: `AppDocumentRoot._render()` is the top of the render tree. Making it async and using sequential child rendering enables parallelism. The DI scope and app context management are preserved.

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

### Decision 8: Unified browser callback scheduler for signal-driven updates

**Chosen**: In the browser environment, all signal callbacks (both sync functions like `_update_text` and async coroutines like `_refresh`) are dispatched through a single unified scheduler (`_BrowserCallbackScheduler`). The scheduler batches all callbacks from one signal propagation wave and executes them sequentially in a single async task (next microtick).

In server/test environments, signal callbacks continue to execute synchronously (unbatched) for backward compatibility.

**Why a unified scheduler**: The previous approach had two execution layers — synchronous callbacks (`_update_text`, attribute updaters) executed immediately, while async callbacks (`_refresh`, `_reconcile_children`) were scheduled via `aio_run()` (fire-and-forget). This interleaving caused execution order bugs:

```
signal change → [sync] _update_text("off") on detached node
              → [async scheduled] SwitchElement._refresh() → creates new DOM tree
              → new TextElement never gets updated
```

The unified scheduler eliminates this split by routing ALL callbacks through the same enqueue→flush pipeline:

```
signal change → enqueue(_update_text, "off")
              → enqueue(_refresh)
              → [next microtick] flush:
                  1. _update_text("off") → updates old node (still in DOM)
                  2. _refresh() → destroys old node, creates new DOM tree
                  3. new TextElement reads current signal value → correct ✅
```

**Implementation**:

```python
# webcompy/aio/_aio.py
class _BrowserCallbackScheduler:
    _queue: list[tuple[Callable, Any]]
    _flushing = False

    @classmethod
    def enqueue(cls, callback, value):
        cls._queue.append((callback, value))
        if not cls._flushing:
            cls._flushing = True
            asyncio.ensure_future(cls._flush())

    @classmethod
    async def _flush(cls):
        while cls._queue:
            batch = cls._queue
            cls._queue = []
            for callback, value in batch:
                try:
                    if iscoroutinefunction(callback):
                        await callback(value)
                    else:
                        callback(value)
                except Exception as err:
                    _log_error(err)
                await asyncio.sleep(0)
        cls._flushing = False
```

```python
# webcompy/signal/_base.py — CallbackConsumerNode._on_marked_dirty()
def _on_marked_dirty(self) -> None:
    if self._is_before:
        return
    from webcompy.signal._computed import Computed
    old_version = self._producer.version
    producer_update_value_version(self._producer)
    self.dirty = False
    if isinstance(self._producer, Computed) and self._producer.version <= old_version:
        return
    if ENVIRONMENT == "pyscript":
        from webcompy.aio._aio import _BrowserCallbackScheduler
        _BrowserCallbackScheduler.enqueue(self._callback, self._producer._value)
    else:
        if iscoroutinefunction(self._callback):
            coro = self._callback(self._producer._value)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(coro)
            else:
                import nest_asyncio
                if not getattr(loop, "_nest_asyncio_patched", False):
                    nest_asyncio.apply(loop)
                    loop._nest_asyncio_patched = True
                loop.run_until_complete(coro)
        else:
            self._callback(self._producer._value)
```

**What this replaces**: The `_make_signal_callback()` wrapper is removed. `RepeatElement._refresh` and `SwitchElement._refresh` register directly as `self._sequence.on_after_updating(self._refresh)` (no wrapper). All callbacks — sync `_update_text` and async `_refresh` alike — go through the scheduler.

**Comparison to other frameworks**:

| Framework | Approach | WebComPy Equivalent |
|-----------|----------|---------------------|
| Vue 3 | `queueJob()` + `Promise.then(flushJobs)` | `_BrowserCallbackScheduler.enqueue()` + `ensure_future(flush)` |
| Svelte | `dirty_components` + `Promise.then(flush)` | Same pattern |
| SolidJS | Synchronous execution (batch() defers effects) | WebComPy uses async batching for browser, sync for server/test |

The `asyncio.sleep(0)` between callbacks during flush ensures that if one callback triggers a new signal change (cascading), the resulting callbacks are enqueued and processed in the same flush pass (via the `while cls._queue` loop). This matches Svelte's `do...while` pattern for cascading updates.

**Why not synchronous execution in browser**: `nest-asyncio` is not available in PyScript/Emscripten. Using `loop.run_until_complete()` to synchronously await async `_refresh()` callbacks would crash the browser. Asynchronous scheduling is the only option.

**Risk**: Delay between signal change and DOM update. The first callback from a batch executes on the next microtick (via `ensure_future`). The `asyncio.sleep(0)` yields between callbacks mean multi-callback batches may take multiple event loop ticks to fully process. This is consistent with Vue/Svelte's approach and is not perceptible to users (browser paints are batched at 60fps). All callbacks from one flush cycle complete before the next paint frame.

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

### Decision 12: Browser callback scheduler in `_aio.py`

**Chosen**: Add `_BrowserCallbackScheduler` class to `webcompy/aio/_aio.py` that provides `enqueue(callback, value)` and `_flush()` methods. The scheduler batches all callbacks from one signal propagation wave and executes them in order within a single async task. The `_make_signal_callback()` utility is removed — all callbacks (sync and async) go through the scheduler.

**Rationale**: See Decision 8 for the detailed rationale. The scheduler replaces the fire-and-forget `_make_signal_callback` wrapper with a deterministic enqueue→flush pipeline that preserves callback execution order.

### Decision 13: Test suite uses pytest-asyncio instead of asyncio.run()

**Chosen**:
- Add `pytest-asyncio` and `nest-asyncio` to dev dependencies in `pyproject.toml`
- Configure `asyncio_mode = "auto"` in `[tool.pytest.ini_options]`
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

## Risks / Trade-offs

- **Breaking change for `generate_html()` callers**: All code that calls `generate_html()` must now `await` it. This affects `_generate.py` and `_server.py` but is limited to the CLI layer.
- **`asyncio.gather()` in Emscripten**: PyScript's `asyncio` implementation handles `asyncio.gather()` correctly for cooperative multitasking. Since all DOM operations happen on the main thread and there's no true parallelism, sibling parallelism provides structural clarity but not performance benefit in the browser.
- **Signal callback adaptation**: Wrapping async `_refresh()` callbacks with `_make_signal_callback()` adds a small overhead per signal update. This is negligible for typical applications.
- **`Component.__init__` remains synchronous**: Async component definitions are not supported in this change. The component setup function must return an `ElementChildren` synchronously. This is a deliberate scope limitation — async component definitions will be added in a follow-up change.
- **Test migration effort**: Converting 20 test files with 69 `asyncio.run()` calls to `await` is a mechanical but time-consuming task. Mistakes during conversion could introduce subtle test failures.