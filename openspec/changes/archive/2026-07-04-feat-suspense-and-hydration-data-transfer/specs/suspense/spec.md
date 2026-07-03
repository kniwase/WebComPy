# Suspense

## Purpose

`Suspense` is a declarative async boundary that shows fallback content while children are loading and swaps to real content when complete. It bridges the gap between WebComPy's fully async rendering pipeline (introduced in `feat/async-rendering-pipeline`) and user-facing loading UI: developers no longer need to manage `useAsyncResult` fire-and-forget patterns for server-side data fetching, and on the client they no longer see flash-of-loading for data that was already resolved during SSR.

`Suspense` is implemented as a `DynamicElement` (`SuspenseElement`) following the same pattern as `SwitchElement` and `RepeatElement`. A `suspense()` generator function is provided in `webcompy.elements.generators` matching the `switch()`/`repeat()` API style.

## ADDED Requirements

### Requirement: Suspense shall be a DynamicElement

`SuspenseElement` SHALL extend `DynamicElement` and SHALL store a no-op `_on_set_parent()` (no signal subscriptions are required). `SuspenseElement` SHALL accept `fallback` (a `Callable[[], ChildNode]` generator), `children` (a `Callable[[], ChildNode]` generator), optional `error_fallback` (a `Callable[[], ChildNode]` generator), and optional `timeout` (a `float` in seconds, default `10.0`).

#### Scenario: Suspense is registered as a DynamicElement
- **WHEN** `SuspenseElement` is instantiated with `fallback`, `children`, and optional `error_fallback` / `timeout` parameters
- **THEN** it SHALL be a subclass of `DynamicElement`
- **AND** it SHALL store the children generator, fallback generator, and any optional `error_fallback` and `timeout` values
- **AND** the `children()` callable SHALL NOT be called during `__init__`; the call SHALL be deferred to `_render()`

### Requirement: Suspense children shall be lazy

The `children` parameter SHALL be `Callable[[], ChildNode]` (a zero-argument function) and SHALL be invoked only when `SuspenseElement` is ready to render children. The `fallback` parameter SHALL also be `Callable[[], ChildNode]` for consistency. This lazy-evaluation pattern mirrors the `switch()` API where generators are called conditionally.

#### Scenario: Children generator is not called until Suspense is ready
- **WHEN** `SuspenseElement.__init__(fallback, children, ...)` stores a `children` callable
- **THEN** `children()` SHALL NOT be called during `__init__`
- **AND** the call to `children()` SHALL be deferred to `_render()`

### Requirement: Suspense shall await children during SSR/SSG

In non-pyscript (server) environments, `SuspenseElement._render()` SHALL wait for all unresolved async child setups before completing its own render. Specifically: the function SHALL provide `SUSPENSE_RESOLVING_KEY=True` in the DI scope, traverse the children subtree to collect each unresolved `Component._pending_async_template` coroutine, and `await asyncio.wait_for(asyncio.gather(*coroutines), timeout=timeout)`. On success, each component's template SHALL be set, `__init_component()` SHALL be called, and `_pending_async_template` SHALL be cleared. On timeout, the fallback SHALL be rendered and a warning SHALL be logged. On exception, if `error_fallback` is provided, it SHALL be rendered; otherwise the exception SHALL propagate to the root render.

#### Scenario: SSR/SSG awaits async children
- **WHEN** `SuspenseElement._render()` runs in a non-pyscript environment and its children subtree contains `Component` instances with unresolved `_pending_async_template` coroutines
- **THEN** the coroutines SHALL be gathered and awaited with a timeout
- **AND** the children SHALL be rendered with their resolved templates in the SSR output (no fallback in the final HTML)
- **AND** the resolved data SHALL be available for the transfer payload collection that runs after the render

#### Scenario: SSR/SSG timeout renders fallback
- **WHEN** `SuspenseElement._render()` runs in a non-pyscript environment and the children async setup does not complete within `timeout` seconds
- **THEN** the fallback SHALL be rendered into the output
- **AND** a warning SHALL be logged indicating which Suspense timed out

### Requirement: Suspense shall render fallback first in the browser then swap

In the pyscript (browser) environment, `SuspenseElement._render()` SHALL first render the fallback, then schedule async child resolution. When the children complete, `_resolve()` SHALL be called to swap the fallback for the children using `_patch_children()`.

#### Scenario: Browser shows fallback immediately
- **WHEN** `SuspenseElement._render()` runs in the pyscript environment and its children have unresolved async setup
- **THEN** the fallback SHALL be rendered into the DOM
- **AND** async child resolution SHALL be scheduled via `asyncio.ensure_future()`

#### Scenario: Browser swaps fallback for resolved children
- **WHEN** the async child resolution scheduled by `SuspenseElement._render()` completes
- **THEN** `_resolve()` SHALL be called
- **AND** the fallback children SHALL be replaced with the resolved children using `_patch_children()`

### Requirement: Suspense shall catch async exceptions and render error_fallback

`SuspenseElement._render()` SHALL wrap the `await asyncio.gather(*coroutines)` call in a `try/except`. If an exception is raised and `error_fallback` is provided, `_handle_error()` SHALL render `error_fallback` via `_patch_children()`. If `error_fallback` is not provided, the exception SHALL propagate to the caller per the foundation's sequential short-circuit semantics. The foundation's `ElementWithChildren._render()` and `DynamicElement._refresh()` loops SHALL NOT have a general `try/except` — adding one would conflict with sequential short-circuit semantics.

#### Scenario: Async child raises with error_fallback provided
- **WHEN** an async child setup raises an exception and `error_fallback` is provided to the enclosing `SuspenseElement`
- **THEN** `error_fallback` SHALL be rendered in place of the fallback
- **AND** the pending async state SHALL be cleared
- **AND** no other async tasks SHALL leak

#### Scenario: Async child raises without error_fallback
- **WHEN** an async child setup raises an exception and `error_fallback` is NOT provided
- **THEN** the exception SHALL propagate out of `SuspenseElement._render()`
- **AND** it SHALL NOT be swallowed at the Suspense level
- **AND** if no enclosing `SuspenseElement` exists, the root render's `resolve_async(..., on_error=_log_error)` hook SHALL log the exception

#### Scenario: Sibling element render is unaffected by failing Suspense
- **WHEN** a `SuspenseElement` is a sibling of another element and the Suspense's child async setup raises (with no `error_fallback`)
- **THEN** the exception SHALL propagate from the Suspense per the foundation's short-circuit semantics
- **AND** `ElementWithChildren._render()` SHALL NOT wrap the await in a `try/except`
- **AND** subsequent siblings SHALL NOT be rendered (sequential short-circuit)

### Requirement: Sibling Suspense elements shall render sequentially

Multiple `Suspense` siblings SHALL render one-by-one via `await`, NOT concurrently via `asyncio.gather()`. This matches the `async-rendering` spec's foundational sibling-rendering rule. Within a single `Suspense` boundary, async children SHALL resolve concurrently via `asyncio.gather(*coroutines)`.

#### Scenario: Multiple sibling Suspense elements render sequentially
- **WHEN** an `ElementWithChildren._render()` has multiple `SuspenseElement` children
- **THEN** `await suspense1._render()` SHALL be called first
- **AND** after suspense1 completes, `await suspense2._render()` SHALL be called
- **AND** after suspense2 completes, `await suspense3._render()` SHALL be called
- **AND** the parent SHALL continue only after all Suspense children complete

### Requirement: Suspense shall coordinate with SUSPENSE_RESOLVING_KEY

`SUSPENSE_RESOLVING_KEY: InjectKey[bool]` SHALL be provided with value `True` by `SuspenseElement._render()` (scoped to the Suspense subtree) and absent (`False` or not provided) in all other contexts. When `SUSPENSE_RESOLVING_KEY` is `True`, `Component._render()` SHALL skip the `_pending_async_template` resolution block entirely — Suspense is responsible for resolving it. When the value is `False` or the key is not provided, `Component._render()` SHALL await `_pending_async_template` directly.

`SUSPENSE_RESOLVING_KEY` SHALL be defined in `packages/webcompy/src/webcompy/di/_keys.py` as `InjectKey[bool]` and exported from `packages/webcompy/src/webcompy/di/__init__.py`.

#### Scenario: Child component defers to Suspense when key is provided
- **WHEN** `SUSPENSE_RESOLVING_KEY` is provided with value `True` in the DI scope during `Component._render()` and the component has `_pending_async_template` set
- **THEN** `Component._render()` SHALL NOT call `await self._pending_async_template`
- **AND** the Suspense boundary SHALL be responsible for the resolution

#### Scenario: Child component resolves its own template when key is absent
- **WHEN** `SUSPENSE_RESOLVING_KEY` is not provided (or `False`) in the DI scope during `Component._render()` and the component has `_pending_async_template` set
- **THEN** `Component._render()` SHALL `await self._pending_async_template` directly
- **AND** the resolved template SHALL be set, `_pending_async_template` SHALL be cleared, and `__init_component()` SHALL be called

### Requirement: Suspense shall expose a suspense() generator function

A `suspense()` function SHALL be exported from `packages/webcompy/src/webcompy/elements/generators.py` with the signature `def suspense(*, fallback: NodeGenerator, children: NodeGenerator, error_fallback: NodeGenerator | None = None, timeout: float = 10.0) -> SuspenseElement`. A `Suspense` alias for `SuspenseElement` SHALL be exported from `packages/webcompy/src/webcompy/elements/__init__.py`.

#### Scenario: Calling suspense() creates a SuspenseElement
- **WHEN** a developer calls `suspense(fallback=..., children=...)`
- **THEN** it SHALL return a `SuspenseElement` instance configured with the provided parameters

#### Scenario: Suspense is importable from webcompy.elements
- **WHEN** a developer writes `from webcompy.elements import Suspense`
- **THEN** the import SHALL succeed
- **AND** `Suspense` SHALL be usable as a class to construct a `SuspenseElement` directly

### Requirement: Suspense hydration shall use has_resolved_data

`SuspenseElement._hydrate_node()` SHALL call `has_resolved_data(component_id)` (from the `hydration-data-transfer` capability) for each child component to decide whether to render the children immediately or keep the fallback. If `True` for all children, the children SHALL be rendered directly. If `False` (or the payload is missing) for any child, the fallback SHALL be hydrated and async resolution SHALL be scheduled.

#### Scenario: Suspense hydrates children directly when data is in payload
- **WHEN** `SuspenseElement._hydrate_node()` runs in the browser and `has_resolved_data(component_id)` returns `True` for all children
- **THEN** the resolved children SHALL be rendered directly
- **AND** the fallback SHALL NOT appear in the DOM after hydration

#### Scenario: Suspense hydrates fallback when data is not in payload
- **WHEN** `SuspenseElement._hydrate_node()` runs in the browser and `has_resolved_data(component_id)` returns `False` for any child
- **THEN** the fallback SHALL be hydrated
- **AND** async resolution SHALL be scheduled to swap fallback for resolved children when the data arrives
