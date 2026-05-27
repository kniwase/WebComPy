# Async Rendering Pipeline

## Purpose

The rendering pipeline supports async component definitions, async lifecycle hooks, and sibling parallel rendering. When a component definition, lifecycle hook, or child rendering involves an async operation, the pipeline awaits it. Existing synchronous code continues to work without modification — `inspect.iscoroutinefunction()` transparently detects async callables and awaits them, while sync callables execute directly.

This enables future async SSR capabilities (per-route data fetching, streaming) and allows developers to use `async def` lifecycle hooks for I/O-bound operations (API calls, async resource loading) without blocking the event loop.

## ADDED Requirements

### Requirement: The rendering pipeline shall support async _render() methods

`ElementAbstract._render()`, `ElementWithChildren._render()`, `DynamicElement._render()`, `RepeatElement._render()`, `SwitchElement._render()`, `Component._render()`, and `AppDocumentRoot._render()` SHALL be `async def` methods. All callers of these methods SHALL `await` them. The `_mount_node()` method SHALL remain synchronous since DOM operations are not async.

`_hydrate_node()` SHALL remain synchronous in this change. Async component setup (`_pending_async_template`) is NOT resolved during hydration — resolution happens during the first async `_render()` after hydration completes. In the browser, components that were pre-resolved during SSR receive their state from the hydration data transfer payload (per `feat-hydration-data-transfer`), so async setup does not need to re-execute. Components without transfer data proceed through the normal async lifecycle during `_render()`, after DOM adoption is complete.

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

### Requirement: Sibling children shall render in parallel via asyncio.gather()

`ElementWithChildren._render()` and `AppDocumentRoot._render()` SHALL use `asyncio.gather()` to render all child elements concurrently. Each child's `_render()` SHALL be scheduled as a separate coroutine. This enables future I/O-bound parallelism during SSG and structural clarity for the async pipeline.

This is a behavioral change from the current sequential rendering pipeline. With sync rendering, children are processed one by one and an exception in child N aborts rendering immediately (children N+1 are never rendered). With `asyncio.gather(return_exceptions=True)`, ALL children render regardless of individual failures — after completion, the first exception is re-raised and `ElementWithChildren._render()` cleans up successfully rendered children via `_remove_element()` before re-raising. In the browser, `asyncio.gather()` provides structural clarity but not true parallelism; the parallel rendering benefit applies to SSG (CPython) only.

#### Scenario: Rendering multiple sibling children
- **WHEN** `ElementWithChildren._render()` is called with 3 children
- **THEN** `asyncio.gather(child1._render(), child2._render(), child3._render())` SHALL be awaited
- **AND** all 3 children SHALL complete rendering before the parent continues

#### Scenario: Sibling rendering preserves DOM order
- **WHEN** children are rendered via `asyncio.gather()`
- **THEN** DOM node indices (`_node_idx`) SHALL be assigned before rendering begins
- **AND** the final DOM order SHALL match the children list order regardless of completion order

#### Scenario: One child raises during sibling rendering
- **WHEN** `asyncio.gather(*tasks, return_exceptions=True)` is used
- **AND** one child's `_render()` raises an unexpected exception
- **THEN** the exception SHALL be captured as a return value (not propagated to cancel sibling tasks)
- **AND** the other sibling children SHALL complete normally
- **AND** after all siblings complete, the first exception encountered SHALL be re-raised
- **AND** `ElementWithChildren._render()` SHALL catch the re-raised exception
- **AND** it SHALL call `_remove_element()` on each successfully rendered child to clean up their DOM nodes
- **AND** `_remove_element()` on each child SHALL trigger the full destruction lifecycle: effect scope disposal, `on_before_destroy` hooks, and DI scope cleanup
- **AND** if `_remove_element()` itself raises during cleanup of a sibling, the exception SHALL be logged via `report_error()` and cleanup SHALL continue for remaining siblings
- **AND** the originally re-raised exception from the failing child SHALL take priority over cleanup errors
- **AND** after cleanup, the exception SHALL be re-raised to its caller
- **AND** no partially rendered sibling nodes SHALL remain orphaned in the DOM

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

When an async callable is registered as a signal callback via `SignalBase.on_after_updating()`, the signal system SHALL schedule the callback via `aio_run()` (which uses `asyncio.ensure_future()` in the browser or `loop.create_task()` on the server). A utility function `_make_signal_callback()` SHALL wrap async callables for transparent scheduling. If an async signal callback raises an exception, the error SHALL be logged via the framework's error reporting mechanism (`webcompy.exception.report_error()`) and SHALL NOT crash the application.

#### Scenario: Registering an async _refresh() as a signal callback
- **WHEN** `RepeatElement._refresh()` is `async def` and registered via `self._sequence.on_after_updating(self._refresh)`
- **THEN** `_make_signal_callback(self._refresh)` SHALL wrap it as a sync callable that calls `aio_run(self._refresh(*args))`
- **AND** the signal system SHALL invoke the wrapped callback normally

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