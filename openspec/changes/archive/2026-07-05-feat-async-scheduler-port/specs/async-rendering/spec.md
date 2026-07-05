## MODIFIED Requirements

### Requirement: The rendering pipeline shall support async _render() methods

`ElementAbstract._render()`, `ElementWithChildren._render()`, `DynamicElement._render()`, `RepeatElement._render()`, `SwitchElement._render()`, `Component._render()`, and `AppDocumentRoot._render()` SHALL be `async def` methods. All callers of these methods SHALL `await` them. The `_mount_node()` method SHALL remain synchronous since DOM operations are not async.

`_hydrate_node()` SHALL remain synchronous in this change. `ElementAbstract._hydrate_node()`, `ElementWithChildren._hydrate_node()`, and `DynamicElement._hydrate_node()` SHALL be `def` methods. All `_hydrate_node()` callers SHALL call them directly (no `await`). `DynamicElement._hydrate_node()` SHALL schedule the async render of unmounted children via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(child._render())`, attaching a done callback that logs exceptions via `webcompy.logging.error`. This eliminates the `RuntimeWarning: coroutine ... was never awaited` and ensures async render errors surface in the log, while routing all task scheduling through the central port so that server-side renders guarantee task completion before context disposal.

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

### Requirement: Sync-only leaf elements shall inherit a default no-op async _render()

`Element._render()` (the base class inherited by `TextElement`, `VoidElement`, `InputElement`, and other sync-only leaf elements) SHALL be `async def` but SHALL have a default implementation with no `await` points. `_mount_node()` is called synchronously (not awaited) since it remains a sync method. The `async def` signature makes the method a coroutine that resolves immediately, so callers can `await` it without change. Custom user elements that override `_render()` SHALL follow the same pattern: if their `_render()` contains no async operations, `async def _render(self)` with no `await` points is valid Python and SHALL work correctly.

#### Scenario: TextElement._render() remains sync internally
- **WHEN** `await TextElement._render()` is called
- **THEN** the text node SHALL be mounted synchronously
- **AND** no `await` point SHALL exist in the method body

### Requirement: Sibling children shall render sequentially via await

`ElementWithChildren._render()` SHALL iterate over children and `await child._render()` for each child sequentially. Children SHALL NOT be rendered concurrently via `asyncio.gather()` in this change. The sequential ordering preserves DOM node index assignment correctness and short-circuit error propagation. Parallel rendering via `asyncio.gather()` is identified as future work requiring ContextVar isolation and atomic sibling cleanup.

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
