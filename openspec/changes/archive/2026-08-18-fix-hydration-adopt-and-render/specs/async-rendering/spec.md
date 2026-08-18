# Async Rendering Pipeline — Hydration "Adopt & Render" Deltas

## MODIFIED Requirements

### Requirement: The rendering pipeline shall support async _render() methods

`ElementAbstract._render()`, `ElementWithChildren._render()`, `DynamicElement._render()`, `RepeatElement._render()`, `SwitchElement._render()`, `Component._render()`, and `AppDocumentRoot._render()` SHALL be `async def` methods. All callers of these methods SHALL `await` them. The `_mount_node()` method SHALL remain synchronous since DOM operations are not async.

`_hydrate_node()` SHALL remain synchronous in this change. `ElementAbstract._hydrate_node()`, `ElementWithChildren._hydrate_node()`, and `DynamicElement._hydrate_node()` SHALL be `def` methods. All `_hydrate_node()` callers SHALL call them directly (no `await`). `DynamicElement._hydrate_node()` SHALL schedule the hydration render of ALL of its children — including children whose nodes were adopted (mounted) — via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(...)`, attaching a done callback that logs exceptions via `webcompy.logging.error`. Attaching the render for adopted children SHALL NOT double-render: the hydration render of a child SHALL be scheduled exactly once (either by the hydrating parent's pass or by an ancestor dynamic container's pass), and containers relying on the hydration-render flag SHALL continue to suppress the inline render chain for their children during the initial hydration. This eliminates the `RuntimeWarning: coroutine ... was never awaited`, ensures async render errors surface in the log, ensures adopted children complete their render (reactive setup), and routes all task scheduling through the central port so that server-side renders guarantee task completion before context disposal.

#### Scenario: Rendering a component in the browser
- **WHEN** `app.run()` is called in the browser
- **THEN** the async render pipeline SHALL be scheduled via `resolve_async(ctx._root._render())`
- **AND** the component tree SHALL render correctly as before

#### Scenario: Rendering a component during SSG
- **WHEN** `generate_html()` is called during static site generation
- **THEN** `await app_root._render()` SHALL be called within the async pipeline
- **AND** the HTML output SHALL match the previous synchronous output

#### Scenario: Backward compatibility of sync _render() callers
- **WHEN** existing code calls `await element._render()` on an element that performs no async operations
- **THEN** the behavior SHALL be identical to the previous synchronous `_render()` call

#### Scenario: Adopted child of a hydrated dynamic container is rendered exactly once
- **WHEN** hydration adopts a child of a dynamic container from prerendered DOM
- **THEN** exactly one hydration render SHALL be scheduled for that child
- **AND** the inline render chain SHALL NOT render the same child during the initial hydration pass

## ADDED Requirements

### Requirement: The browser async scheduler shall drain scheduled render tasks on await_pending

`BrowserAsyncSchedulerPort.await_pending(only_render=True)` SHALL await completion of the render tasks scheduled through the scheduler that have not yet completed, before returning. Render tasks SHALL be marked at scheduling time via `schedule(coro, render=True)`; the framework's hydration/render call sites (`DynamicElement._hydrate_node` child renders, Teleport's post-hydration render, ErrorBoundary `_do_reset`) SHALL mark their tasks. Tasks scheduled without the flag (generic `aio_run` work such as user fetches) SHALL NOT block the call. Completed tasks SHALL NOT be awaited again (the call SHALL be idempotent with respect to already-finished tasks). Exceptions raised by scheduled tasks SHALL NOT propagate through `await_pending()` (they surface via the scheduler's done-callback logging path as before). This mirrors the server scheduler's drain guarantee and gives the browser hydration pipeline a completion point.

#### Scenario: Scheduled hydration renders complete before the drain returns
- **WHEN** browser hydration schedules route-component render tasks with `render=True`
- **AND** `AppDocumentRoot._render()` awaits `await_pending(only_render=True)`
- **THEN** `await_pending()` SHALL NOT return until the scheduled render tasks have finished (or failed with logged errors)
- **AND** the routed content SHALL be present in the DOM afterwards

#### Scenario: Non-render tasks do not block the drain
- **WHEN** a long-running non-render task (e.g., a user fetch scheduled via `aio_run`) is pending
- **AND** `await_pending(only_render=True)` is called
- **THEN** the call SHALL return once the render-marked tasks complete, regardless of the non-render task's state

#### Scenario: await_pending with no pending tasks returns immediately
- **WHEN** `await_pending()` is called and no tasks are pending
- **THEN** the call SHALL return without error

### Requirement: AppDocumentRoot shall drain hydration tasks before removing the loading indicator

In browser hydration mode, `AppDocumentRoot._render()` SHALL await the scheduler drain (`inject(ASYNC_SCHEDULER_PORT_KEY).await_pending(only_render=True)`) before removing the `#webcompy-loading` element. When the loading indicator is removed, the routed page content SHALL already be present in the DOM (adopted prerendered nodes included), so the reveal never shows a page with missing route content. The drain SHALL NOT wait for non-render tasks, so unrelated slow user work does not delay the reveal.

#### Scenario: Loading indicator removal happens after route content is present
- **WHEN** `app.run()` hydrates an SSR page whose route content is rendered by scheduled tasks
- **THEN** the `#webcompy-loading` element SHALL be removed only after the scheduled renders complete
- **AND** querying the routed content (e.g., the page component's root node) SHALL succeed at the moment of removal

#### Scenario: Non-hydration render path is unaffected
- **WHEN** the framework runs in a non-`pyscript` environment
- **THEN** the server-side render contract SHALL remain unchanged (the await chain completes before `generate_html` returns)

### Requirement: Hydration mismatch records shall be aggregated and exposed

After the hydration pass and the drain complete, the app SHALL aggregate the mismatch records collected at the element level (see the elements capability). If records exist, exactly ONE console warning SHALL be emitted, summarizing the mismatch count by class (text, attribute, tag, node-count) and by owning component ID. If no records exist, no hydration-mismatch message SHALL be logged. `RenderContext` SHALL expose a `hydration_report` attribute containing the full records (class, expected value, actual value, owning component ID each) for tests and tooling; it SHALL be an empty collection when hydration produced no mismatches, and SHALL be unavailable/empty before hydration runs.

#### Scenario: Matching hydration produces no warning
- **WHEN** browser hydration of an SSR page completes without mismatches
- **THEN** no hydration-mismatch warning SHALL be logged
- **AND** `RenderContext.hydration_report` SHALL be empty

#### Scenario: Mismatching hydration produces a single aggregated warning
- **WHEN** browser hydration produces mismatches in several elements of one or more components
- **THEN** a single console warning SHALL summarize the mismatch counts by class and component
- **AND** `RenderContext.hydration_report` SHALL contain one record per mismatch with class, expected, actual, and component ID

#### Scenario: Report available before hydration is empty
- **WHEN** `RenderContext.hydration_report` is read before the hydration pass has run (or on the server)
- **THEN** it SHALL be an empty collection