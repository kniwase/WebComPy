# Async Rendering Pipeline

## Purpose

The rendering pipeline supports async component definitions, async lifecycle hooks, and sibling parallel rendering. When a component definition, lifecycle hook, or child rendering involves an async operation, the pipeline awaits it. Existing synchronous code continues to work without modification — `inspect.iscoroutinefunction()` transparently detects async callables and awaits them, while sync callables execute directly.

This enables future async SSR capabilities (per-route data fetching, streaming) and allows developers to use `async def` lifecycle hooks for I/O-bound operations (API calls, async resource loading) without blocking the event loop.

## ADDED Requirements

### Requirement: The rendering pipeline shall support async _render() methods

`ElementAbstract._render()`, `ElementWithChildren._render()`, `DynamicElement._render()`, `RepeatElement._render()`, `SwitchElement._render()`, `Component._render()`, and `AppDocumentRoot._render()` SHALL be `async def` methods. All callers of these methods SHALL `await` them. The `_mount_node()` method SHALL remain synchronous since DOM operations are not async.

 `_hydrate_node()` SHALL become async in this change. `ElementAbstract._hydrate_node()`, `ElementWithChildren._hydrate_node()`, and `DynamicElement._hydrate_node()` SHALL be `async def` methods. All internal callers SHALL `await` them. `DynamicElement._hydrate_node()` SHALL `await child._render()` for unmounted children instead of calling `child._render()` synchronously (which would produce an un-awaited coroutine and a RuntimeWarning).

#### Scenario: Rendering a component in the browser
- **WHEN** `app.run()` is called in the browser
- **THEN** the async render pipeline SHALL be scheduled via `asyncio.ensure_future(self._root._render())`
- **AND** the component tree SHALL render correctly as before

#### Scenario: Rendering a component during SSG
- **WHEN** `generate_html()` is called during static site generation
- **THEN** `await app_root._render()` SHALL be called within the async pipeline
- **AND** the HTML output SHALL match the previous synchronous output

#### Scenario: Backward compatibility of sync _render() callers
- **WHEN** existing code calls `await element._render()` on an element that performs no async operations
- **THEN** the behavior SHALL be identical to the previous synchronous `_render()` call

### Requirement: Sync-only leaf elements shall inherit a default no-op async _render()

`Element._render()` (the base class inherited by `TextElement`, `VoidElement`, `InputElement`, and other sync-only leaf elements) SHALL be `async def` but SHALL have a default implementation with no `await` points. `_mount_node()` is called synchronously (not awaited) since it remains a sync method. The `async def` signature makes the method a coroutine that resolves immediately, so callers can `await` it without change. This is valid Python — an `async def` method with no `await` expressions returns a coroutine that completes on first `await`. The spec explicitly notes: leaf elements' `_render()` SHALL NOT `await self._mount_node()` because `_mount_node()` is synchronous and awaiting a non-coroutine would cause a TypeError. Custom user elements that override `_render()` SHALL follow the same pattern: if their `_render()` contains no async operations, `async def _render(self)` with no `await` points is valid Python and SHALL work correctly. This is not a breaking change — calling `await element._render()` on a coroutine with no `await` points behaves identically to a synchronous call.

#### Scenario: TextElement._render() remains sync internally
- **WHEN** `TextElement._render()` is called as `await text._render()`
- **THEN** the method SHALL be `async def` but SHALL contain zero `await` expressions
- **AND** the text node SHALL be mounted to the DOM identically to the pre-async behavior

#### Scenario: VoidElement._render() remains sync internally
- **WHEN** `VoidElement._render()` (e.g., `<br>`, `<img>`) is called
- **THEN** SHALL complete without performing any actual async I/O
- **AND** the element SHALL be mounted correctly

#### Scenario: User-defined sync element overrides _render()
- **WHEN** a developer subclasses `ElementWithChildren` and overrides `_render()` as `async def` with no await points
- **THEN** calling `await element._render()` SHALL work identically to a sync override
- **AND** no special migration steps SHALL be required

### Requirement: Sibling children shall render sequentially

`ElementWithChildren._render()` and `AppDocumentRoot._render()` SHALL render child elements sequentially using `for child in self._children: await child._render()`. Each child's `_render()` SHALL be awaited before the next child begins. This preserves the DOM ordering guarantees of the pre-async pipeline and avoids race conditions in DOM manipulation.

This is a behavioral match to the current sequential rendering pipeline. With sync rendering, children are processed one by one and an exception in child N aborts rendering immediately (children N+1 are never rendered). The async pipeline preserves this exact behavior: `await child._render()` for each child in order, and an exception aborts the sequence immediately without rendering subsequent children.

> **Future enhancement**: Parallel rendering via `asyncio.gather()` is identified as a future performance optimization. It will require careful DOM ordering guarantees, atomic cleanup of failed siblings, and ContextVar isolation across concurrent tasks. See the "Future Work" section.

#### Scenario: Rendering multiple sibling children
- **WHEN** `ElementWithChildren._render()` is called with 3 children
- **THEN** `await child1._render()` SHALL be called first
- **AND** after child1 completes, `await child2._render()` SHALL be called
- **AND** after child2 completes, `await child3._render()` SHALL be called
- **AND** the parent SHALL continue only after all 3 children complete

#### Scenario: Sibling rendering preserves DOM order
- **WHEN** children are rendered sequentially
- **THEN** DOM node indices (`_node_idx`) SHALL be assigned before each child renders
- **AND** the final DOM order SHALL match the children list order exactly

#### Scenario: One child raises during sibling rendering
- **WHEN** one child's `_render()` raises an unexpected exception during sequential rendering
- **THEN** the exception SHALL propagate immediately via the `await`
- **AND** subsequent children SHALL NOT be rendered (sequential short-circuit semantics)
- **AND** the exception SHALL be re-raised to the caller
- **AND** any previously rendered siblings SHALL remain in the DOM (no cleanup needed since no siblings were rendered after the failing one)

#### Scenario: _active_consumer and _active_di_scope ContextVar preservation during sequential rendering
- **WHEN** children are rendered sequentially
- **THEN** each child's `_render()` SHALL inherit the parent's ContextVar state naturally via the single `await` chain
- **AND** no manual ContextVar snapshot/restore SHALL be needed for sequential rendering
- **AND** ContextVar state SHALL NOT leak between siblings because siblings execute one at a time

### Requirement: Lifecycle hooks shall support async callables

`on_before_rendering` and `on_after_rendering` hooks SHALL accept both synchronous and asynchronous callables. `Component._render()` SHALL use `inspect.iscoroutinefunction()` to detect async hooks and `await` them. Synchronous hooks SHALL be called directly without wrapping.

#### Scenario: Using a sync on_before_rendering hook
- **WHEN** a component defines `@on_before_rendering def setup(self): ...` (synchronous)
- **THEN** the hook SHALL be called directly during `_render()` without awaiting
- **AND** the behavior SHALL be identical to the pre-async pipeline

#### Scenario: Using an async on_before_rendering hook
- **WHEN** a component defines `@on_before_rendering async def setup(self): ...` (asynchronous)
- **THEN** `Component._render()` SHALL `await` the hook
- **AND** the hook SHALL complete before rendering proceeds

#### Scenario: Using an async on_after_rendering hook
- **WHEN** a component defines `@on_after_rendering async def post_render(self): ...` (asynchronous)
- **THEN** `Component._render()` SHALL `await` the hook after rendering completes
- **AND** the behavior SHALL be identical to sync hooks for DOM update purposes

#### Scenario: Async on_after_rendering during route navigation
- **WHEN** an async `on_after_rendering` hook is deferred via `start_defer_after_rendering()`
- **THEN** the hook SHALL be scheduled via the host port's `schedule_macro_task()` mechanism, which wraps it as `lambda: aio_run(async_hook())` — `aio_run()` internally calls `asyncio.ensure_future()` (browser) or `loop.create_task()` (server)
- **AND** the `schedule_macro_task()` + `aio_run()` pair ensures the hook runs asynchronously within the event loop after the current synchronous execution finishes

### Requirement: Context shall accept async lifecycle hooks

`Context.on_before_rendering()`, `Context.on_after_rendering()`, and `Context.on_before_destroy()` SHALL accept both `Callable[[], Any]` and `Callable[[], Coroutine[Any, Any, Any]]` as arguments. The standalone decorator functions `@on_before_rendering`, `@on_after_rendering`, and `@on_before_destroy` SHALL also accept async callables.

#### Scenario: Registering an async on_before_rendering hook via context method
- **WHEN** a developer calls `context.on_before_rendering(async_hook)` inside a component setup function
- **THEN** the async callable SHALL be stored as the hook
- **AND** `Component._render()` SHALL detect it via `iscoroutinefunction()` and `await` it

#### Scenario: Registering an async on_after_rendering hook via decorator
- **WHEN** a developer uses `@on_after_rendering async def hook(): ...` inside a function-style component
- **THEN** the async callable SHALL be registered as the hook
- **AND** `Component._render()` SHALL `await` it during rendering

### Requirement: ComponentProperty shall accept async lifecycle hooks in its type definition

The `ComponentProperty` TypedDict SHALL type `on_before_rendering`, `on_after_rendering`, and `on_before_destroy` as `Callable[[], Any] | Callable[[], Coroutine[Any, Any, Any]]` to reflect that both sync and async callables are valid.

#### Scenario: Type checking a ComponentProperty with async hooks
- **WHEN** a developer passes an async callable as `on_before_rendering` in a `ComponentProperty`
- **THEN** a type checker SHALL accept it without error

### Requirement: generate_html() shall be async

`generate_html()` SHALL be an `async def` function returning `str`. Callers SHALL `await` it. This applies to both SSG (`_generate.py`) and dev server (`_server.py`) contexts.

#### Scenario: Calling generate_html() during SSG
- **WHEN** `generate_static_site()` calls `await generate_html(app, ...)`
- **THEN** the HTML SHALL be generated correctly
- **AND** the output SHALL match the previous synchronous output

#### Scenario: Calling generate_html() in the dev server
- **WHEN** the Starlette ASGI handler calls `await generate_html(app, ...)`
- **THEN** the HTML SHALL be generated correctly
- **AND** the response SHALL be returned to the client

### Requirement: generate_static_site() shall be async

`generate_static_site()` SHALL be an `async def` function. The CLI entry point SHALL use `asyncio.run()` to call it. Internal calls to `generate_html()` SHALL be awaited.

#### Scenario: Running SSG from CLI
- **WHEN** `python -m webcompy generate` is executed
- **THEN** `asyncio.run(generate_static_site(...))` SHALL be called
- **AND** all route HTML SHALL be generated correctly

### Requirement: app.run() shall schedule the async render

In the browser (PyScript) environment, `app.run()` SHALL schedule the async render via `asyncio.ensure_future(self._root._render())`. This SHALL NOT block the event loop. The loading indicator removal and profile recording SHALL happen within the async render pipeline.

#### Scenario: Running an app in the browser
- **WHEN** `app.run()` is called in a PyScript environment
- **THEN** `asyncio.ensure_future(self._root._render())` SHALL be called
- **AND** the application SHALL render and mount into the DOM correctly

#### Scenario: Calling run() in a non-browser environment
- **WHEN** `app.run()` is called in a non-PyScript environment
- **THEN** a `WebComPyException` SHALL be raised (unchanged behavior)

### Requirement: Dynamic element refresh shall be async

`RepeatElement._refresh()` and `SwitchElement._refresh()` SHALL be `async def` methods. Their signal callback registrations SHALL wrap async callbacks with a scheduling utility (`aio_run()`) so that the signal system can invoke them correctly.

#### Scenario: RepeatElement refresh triggered by signal update
- **WHEN** a `ReactiveList` value changes and `RepeatElement._refresh()` is triggered
- **THEN** the async `_refresh()` SHALL be scheduled via `aio_run()` from the signal callback
- **AND** child rendering SHALL be awaited correctly

#### Scenario: SwitchElement refresh triggered by signal update
- **WHEN** a `Signal` value changes and `SwitchElement._refresh()` is triggered
- **THEN** the async `_refresh()` SHALL be scheduled via `aio_run()` from the signal callback
- **AND** deferred `on_after_rendering` callbacks SHALL be scheduled correctly

### Requirement: Signal callbacks shall support async callables

When an async callable is registered as a signal callback via `SignalBase.on_after_updating()`, the signal system SHALL execute the callback synchronously and block until completion. A utility function `_make_signal_callback()` SHALL wrap async callables for transparent execution. If an async signal callback raises an exception, the error SHALL be logged via the framework's logging mechanism (`logging.error()`) and SHALL NOT crash the application.

This synchronous execution ensures that signal-driven DOM updates (e.g., `RepeatElement._refresh()`, `SwitchElement._refresh()`) complete atomically before any subsequent code runs, preventing race conditions and duplicate DOM elements that would occur with fire-and-forget scheduling.

#### Scenario: Registering an async _refresh() as a signal callback
- **WHEN** `RepeatElement._refresh()` is `async def` and registered via `self._sequence.on_after_updating(self._refresh)`
- **THEN** `_make_signal_callback(self._refresh)` SHALL wrap it as a sync callable that executes the coroutine to completion using `run_sync()` semantics (identical to `webcompy.testing._utils.run_sync()`)
- **AND** the signal system SHALL invoke the wrapped callback normally
- **AND** the callback SHALL complete before the signal setter returns

#### Scenario: Registering a sync _refresh() as a signal callback
- **WHEN** a sync `_refresh()` method is registered as a signal callback
- **THEN** `_make_signal_callback()` SHALL return the callback unchanged
- **AND** the behavior SHALL be identical to the pre-async pipeline

### Requirement: _HtmlElement.render_html() shall be async

`_HtmlElement.render_html()` SHALL be an `async def` method that awaits `self._render()`. This propagates the async pipeline to the SSG layer.

#### Scenario: Generating HTML for SSG
- **WHEN** `_HtmlElement.render_html()` is called during `generate_html()`
- **THEN** `await self._render()` SHALL be called
- **AND** the rendered HTML string SHALL be returned

### Requirement: Tests shall use pytest-asyncio for async test execution

The WebComPy test suite SHALL use `pytest-asyncio` for testing async rendering methods. Test functions that invoke async code SHALL be declared as `async def` and use `await` instead of `asyncio.run()`. All `async def` test functions SHALL be marked with an explicit `@pytest.mark.asyncio` decorator. `asyncio_mode` SHALL NOT be set in `pyproject.toml` (defaults to strict mode, requiring explicit markers).

Test utility functions (e.g., `TestRenderer.render()`, `render_app_html_sync()`) that provide a synchronous interface for test code SHALL use a `run_sync()` helper instead of `asyncio.run()`. The `run_sync()` helper SHALL detect whether it is already inside a running event loop and, if so, use `asyncio.get_event_loop().run_until_complete()` or an equivalent mechanism instead of `asyncio.run()`.

#### Scenario: Testing an element's _render() method
- **WHEN** a test calls `await element._render()` inside an `async def` test function
- **THEN** `pytest-asyncio` SHALL execute the coroutine correctly
- **AND** the test SHALL not raise `RuntimeError: asyncio.run() cannot be called from a running event loop`

#### Scenario: Using TestRenderer in async tests
- **WHEN** a test calls `TestRenderer.render(component)` inside an `async def` test function
- **THEN** the test utility SHALL transparently execute the component's async `_render()`
- **AND** the test SHALL receive a `TestRendererResult` synchronously
- **AND** the utility SHALL work correctly regardless of whether pytest-asyncio's event loop is active

#### Scenario: Running the full test suite
- **WHEN** `uv run python -m pytest tests/` is executed
- **THEN** all unit tests SHALL pass without `asyncio.run()` related errors
- **AND** the test execution time SHALL not increase significantly compared to the sync pipeline

## Future Work

### Parallel Sibling Rendering

Sequential rendering of sibling children is correct and safe but does not exploit the async pipeline's potential for I/O-bound parallelism. A future enhancement may introduce `asyncio.gather()` for sibling rendering with the following prerequisites:

1. **DOM ordering guarantees**: Even with concurrent execution, DOM node indices must be pre-assigned (`_node_idx`) and `insertBefore` calls must use deterministic positions.
2. **Atomic cleanup**: When one sibling raises, all successfully rendered siblings must be atomically removed via `_remove_element()` before the exception propagates. Cleanup errors must be logged and not block continued cleanup.
3. **ContextVar isolation**: In PyScript, `_active_consumer` and `_active_di_scope` must be manually snapshotted and restored per task because PyScript's ContextVar fallback uses shared module-level globals. CPython handles ContextVar isolation natively.
4. **Behavioral compatibility**: The change from sequential short-circuit to all-siblings-execute semantics is a behavioral difference that must be documented. Developers relying on sequential side-effect ordering may need updates.
5. **Testing**: Dedicated tests for parallel rendering scenarios (concurrent siblings, error cleanup, ContextVar isolation) must be added before enabling.

This enhancement is deferred until the above concerns are fully addressed and tested.

### Rendering Queue for Signal-Driven Updates

The current approach executes async signal callbacks synchronously (blocking until completion via `run_sync()` semantics). While this prevents race conditions and duplicate DOM elements, it blocks the event loop during callback execution. A future enhancement may introduce a rendering queue that batches and serializes signal-driven updates:

1. **Queue mechanism**: When a signal updates, instead of immediately executing the callback, enqueue the update request.
2. **Batch processing**: Process the queue at the end of the current event loop tick (via `schedule_macro_task()`), applying all pending updates in order.
3. **Deduplication**: If the same signal updates multiple times in one tick, only process the latest value (intermediate values are skipped).
4. **Atomic render cycles**: Each queued update triggers a single render cycle that completes before the next update begins.
5. **Benefits**: Prevents event loop blocking during individual callbacks while maintaining deterministic render ordering.

This enhancement is deferred until the async rendering pipeline is stable and the duplicate DOM element issue is fully resolved.