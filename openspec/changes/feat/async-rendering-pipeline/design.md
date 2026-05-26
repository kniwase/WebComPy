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
- Changing the testing module for async rendering (separate change)

## Decisions

### Decision 1: `_render()` becomes `async def _render(self)`

**Chosen**: Change `ElementAbstract._render()` from `def _render(self):` to `async def _render(self):`. All overrides in `ElementWithChildren`, `DynamicElement`, `RepeatElement`, `SwitchElement`, `Component`, and `AppDocumentRoot` also become async.

**Rationale**: This is the foundational change. Making `_render()` async allows every render step to `await` async operations (component setup, lifecycle hooks, child rendering). The alternative — keeping `_render()` sync and wrapping async calls with `asyncio.run()` at each call site — would break the event loop in both Emscripten (where the PyScript runtime manages the loop) and CPython (where `asyncio.run()` creates a new loop).

**Key change**: The base method signature changes from `def _render(self):` to `async def _render(self):`. This propagates to every subclass.

### Decision 2: `ElementWithChildren._render()` uses `asyncio.gather()` for sibling parallelism

**Chosen**: Change `ElementWithChildren._render()` to:

```python
async def _render(self):
    await super()._render()
    await asyncio.gather(*[child._render() for child in self._children])
    if (node := self._get_node()) is not None:
        for _ in range(node.childNodes.length - self._children_length):
            node.childNodes[-1].remove()
```

**Rationale**: In the synchronous version, children are rendered sequentially. With async rendering, `asyncio.gather()` allows sibling children to render concurrently. This is safe because each child operates on its own DOM subtree. DOM mutations are sequential within a single child but independent across siblings. In the browser (Emscripten), `asyncio.gather()` still executes coroutines cooperatively on a single thread, so there are no race conditions on the DOM. On the server (SSG), this enables future I/O-bound parallelism.

**Trade-off**: `asyncio.gather()` does not guarantee ordering of coroutine start, but it does guarantee ordering of results. Since DOM child indices are pre-assigned (`_node_idx`) and mounting uses `insertBefore` at specific positions, rendering order is determined by `_node_idx`, not execution order. This means sibling parallelism is safe.

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
    app = _active_app_context.get()
    if app is not None and app._defer_depth > 0:
        app._deferred_callbacks.append(on_after_rendering)
    else:
        if iscoroutinefunction(on_after_rendering):
            await on_after_rendering()
        else:
            on_after_rendering()
```

**Rationale**: `inspect.iscoroutinefunction()` cleanly detects async hooks. This is backward compatible — sync hooks work unchanged. The deferred callback mechanism for `on_after_rendering` (used during `SwitchElement._refresh()`) is preserved.

**Deferred async hooks**: When an async `on_after_rendering` hook is deferred (via `start_defer_after_rendering()`), it is scheduled via `inject(HOST_PORT_KEY).schedule_macro_task()` which already handles async callables (the `schedule_macro_task` method on `HostPort` receives a callback and schedules it). Async deferred hooks are wrapped in `aio_run()` to handle the coroutine.

### Decision 5: `AppDocumentRoot._render()` becomes async

**Chosen**:

```python
async def _render(self):
    token = _active_di_scope.set(self._di_scope)
    app_token = _active_app_context.set(self._app) if self._app else None
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
                child._hydrate_node()
        await asyncio.gather(*[child._render() for child in self._children])
        on_after = self._property["on_after_rendering"]
        if iscoroutinefunction(on_after):
            await on_after()
        else:
            on_after()
        # ... rest (profile, loading removal, etc.) ...
    finally:
        if ENVIRONMENT != "pyscript":
            if app_token is not None:
                _active_app_context.reset(app_token)
            _active_di_scope.reset(token)
```

**Rationale**: `AppDocumentRoot._render()` is the top of the render tree. Making it async and using `asyncio.gather()` for child rendering enables parallelism. The DI scope and app context management are preserved.

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

### Decision 8: `SwitchElement._refresh()` and `RepeatElement._refresh()` become async

**Chosen**: Both `_refresh()` methods become async to support awaiting `_render()` calls on children:

```python
async def _refresh(self, *args):
    # ... same logic, but child._render() is awaited ...
    await asyncio.gather(*[child._render() for child in self._children])
```

**Rationale**: Since `_render()` is now async, `_refresh()` must also be async to await it. The signal callback mechanism (`on_after_updating(self._refresh)`) needs to handle both sync and async callbacks. The `SignalBase.on_after_updating()` mechanism already wraps callbacks — we need to ensure it handles async callbacks correctly.

**Signal callback adaptation**: `SignalBase.on_after_updating()` registers a callback that is called when a signal updates. Currently, `_refresh` is passed directly. With async `_refresh`, the callback is a coroutine function. The signal system needs to detect this and schedule it appropriately:

- In the browser: Use `asyncio.ensure_future()` to schedule the async callback
- On the server: Use `aio_run()` from `webcompy/aio/_aio.py`

We add an `_async_callback_wrapper` utility that wraps an async callback for use with the signal system:

```python
def _make_signal_callback(callback):
    if iscoroutinefunction(callback):
        def wrapper(*args, **kwargs):
            aio_run(callback(*args, **kwargs))
        return wrapper
    return callback
```

This ensures backward compatibility: sync callbacks continue to work directly, while async callbacks are scheduled via the event loop.

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

### Decision 12: `_aio.py` async rendering support

**Chosen**: No changes needed to `_aio.py` for this change. The existing `aio_run()` function already handles scheduling async work in both environments. The `_make_signal_callback()` wrapper (from Decision 8) uses `aio_run()` internally.

**Rationale**: `aio_run()` already provides the infrastructure for scheduling async work. The `_make_signal_callback()` utility is a thin wrapper that uses `aio_run()` for async callbacks.

## Risks / Trade-offs

- **Breaking change for `generate_html()` callers**: All code that calls `generate_html()` must now `await` it. This affects `_generate.py` and `_server.py` but is limited to the CLI layer.
- **`asyncio.gather()` in Emscripten**: PyScript's `asyncio` implementation handles `asyncio.gather()` correctly for cooperative multitasking. Since all DOM operations happen on the main thread and there's no true parallelism, sibling parallelism provides structural clarity but not performance benefit in the browser.
- **Signal callback adaptation**: Wrapping async `_refresh()` callbacks with `_make_signal_callback()` adds a small overhead per signal update. This is negligible for typical applications.
- **`Component.__init__` remains synchronous**: Async component definitions are not supported in this change. The component setup function must return an `ElementChildren` synchronously. This is a deliberate scope limitation — async component definitions will be added in a follow-up change.