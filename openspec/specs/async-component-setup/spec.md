# Async Component Setup

## Purpose

Component setup functions may be `async def`, enabling developers to `await` async operations (API calls, async resource loading) during component initialization. The coroutine is resolved during the async `_render()` phase, making the fetched data available for the initial render. Synchronous component definitions continue to work unchanged — `inspect.iscoroutinefunction()` transparently detects async definitions and uses a two-phase initialization strategy.

## Requirements

### Requirement: Component setup functions may be async def

A component definition decorated with `@define_component(...)` SHALL be `async def`. The async keyword SHALL be detected via `inspect.iscoroutinefunction()`, and the resulting coroutine SHALL be stored and resolved during `_render()`. Synchronous definitions SHALL be initialized immediately as before.

#### Scenario: Defining an async component
- **WHEN** a developer writes `@define_component() async def MyComponent(context): ... return html.DIV({}, "hello")`
- **THEN** the component SHALL be created without error
- **AND** `MyComponent(props)` SHALL return a `Component` instance
- **AND** the component SHALL render correctly when `_render()` is awaited

#### Scenario: Awaiting an async operation during setup
- **WHEN** a developer writes:
  ```python
  @define_component()
  async def MyComponent(context):
      data = await fetch("/api/data")
      return html.DIV({}, str(data))
  ```
- **THEN** `await fetch("/api/data")` SHALL execute on the event loop during `_render()`
- **AND** the resolved `data` SHALL be available when the template is rendered
- **AND** the component SHALL render the fetched data in the DOM

#### Scenario: Sync component continues to work unchanged
- **WHEN** a developer writes `@define_component() def MyComponent(context): return html.DIV({}, "hello")`
- **THEN** the component SHALL initialize immediately in `__init__()`
- **AND** behavior SHALL be identical to pre-async-component-setup

### Requirement: Two-phase initialization for async components

When a component definition is `async def`, initialization SHALL be split into two phases: (1) during `__init__()`, the coroutine is stored in `self._pending_async_template` and `__init_component()` is skipped; (2) during the first `_render()`, the coroutine is awaited, the template is resolved, and `__init_component()` is called to finish initialization.

The coroutine SHALL be set on `self._pending_async_template` during `__init__()` so that it is **observable before `_render()` is called**. This allows `SuspenseElement` to detect pending async operations via tree traversal before any rendering begins. When a component is wrapped in a `Suspense` boundary, `SuspenseElement._render()` owns the resolution — it traverses the tree, collects pending coroutines, awaits them, and then calls `Component._render()` after resolution. `Component._render()` checks whether it is being resolved by a Suspense ancestor (via a context flag) and skips the await step when it is.

#### Scenario: Async component initialization deferred to render
- **WHEN** an async component is created via `MyComponent(props)`
- **THEN** `self._pending_async_template` SHALL contain the unresolved coroutine
- **AND** `self.__init_component()` SHALL NOT be called during `__init__()`
- **AND** the component's `_tag_name`, `_attrs`, and `_children` SHALL be uninitialized (defaults from `ElementBase`)

#### Scenario: Async component resolved during render
- **WHEN** `_render()` is called on an async component with `self._pending_async_template` set
- **AND** the component is NOT wrapped inside a `Suspense` boundary
- **THEN** the coroutine SHALL be awaited to obtain the resolved template
- **AND** `self._pending_async_template` SHALL be set to `None`
- **AND** `self.__init_component()` SHALL be called with the resolved template
- **AND** the component SHALL then proceed with normal async rendering (lifecycle hooks, child rendering)

#### Scenario: Async component under Suspense boundary
- **WHEN** an async component with `self._pending_async_template` set is a descendant of a `SuspenseElement`
- **THEN** `SuspenseElement._render()` SHALL detect the pending state via tree traversal of `_pending_async_template`
- **AND** `Component._render()` SHALL NOT await `_pending_async_template` when the component is flagged as being resolved by a Suspense boundary
- **AND** `SuspenseElement._render()` SHALL handle the await, then call `Component._render()` after resolution
- **AND** fallback SHALL be shown while `_pending_async_template` is pending and observable

#### Scenario: Async component renders only once
- **WHEN** `_render()` is called on an already-resolved async component (second+ render, e.g., after a reactive update)
- **THEN** `self._pending_async_template` SHALL be `None`
- **AND** the component SHALL skip the two-phase init block
- **AND** the component SHALL proceed directly to normal rendering

### Requirement: SUSPENSE_RESOLVING_KEY shall enable Suspense to own async resolution

`SUSPENSE_RESOLVING_KEY` SHALL be defined as `InjectKey[bool]` in `packages/webcompy/src/webcompy/di/_keys.py`. It SHALL be provided with value `True` during `SuspenseElement._render()` (scoped to the Suspense subtree) and absent (`False` or not provided) in all other contexts. When `SUSPENSE_RESOLVING_KEY` is `True`, `Component._render()` SHALL skip the `_pending_async_template` resolution block entirely, regardless of whether `_pending_async_template` is `None` or still set — Suspense is responsible for resolving it (awaiting the coroutine, setting it to `None`, and calling `__init_component()`). When the value is `False` or the key is not provided, `Component._render()` SHALL await `_pending_async_template` directly.

The DI key SHALL be provided in the DI scope during `SuspenseElement._render()` before tree traversal, not in `__init__()`. In the **server environment**, `Suspense._render()` awaits async children and calls `Component._render()` synchronously within the same DI scope (disposed via `finally` after all children render). In the **browser environment**, `Suspense._render()` renders fallback and schedules async resolution via `asyncio.ensure_future()` — the DI scope with `SUSPENSE_RESOLVING_KEY=True` SHALL persist until the async resolution completes (the scope is entered in `_render()` and disposed in the `_resolve()` callback's `finally` block after fallback→children swap). This ensures descendant `Component._render()` calls during the async resolution see `True` for the key.

For nested `Suspense` boundaries, each Suspense SHALL provide its own scope of `SUSPENSE_RESOLVING_KEY`, and descendant Components SHALL see the value from the nearest ancestor Suspense scope. After Suspense resolution completes, the Suspense-provided scope SHALL be disposed (via `finally` block), restoring the outer scope's value.

#### Scenario: SUSPENSE_RESOLVING_KEY is True during Suspense._render()
- **WHEN** `SuspenseElement._render()` is executing
- **THEN** `SUSPENSE_RESOLVING_KEY` SHALL be provided as `True` in the DI scope
- **AND** descendant `Component._render()` calls SHALL see `True` for this key
- **AND** they SHALL skip awaiting `_pending_async_template`

#### Scenario: SUSPENSE_RESOLVING_KEY is absent outside Suspense context
- **WHEN** `Component._render()` is called without a Suspense ancestor
- **THEN** `SUSPENSE_RESOLVING_KEY` SHALL be `False` or not present in the DI scope
- **AND** `Component._render()` SHALL await `_pending_async_template` directly

#### Scenario: Nested Suspense boundaries each provide their own scope
- **WHEN** an inner `Suspense` boundary wraps an async component inside an outer `Suspense` boundary
- **THEN** the inner `Suspense._render()` SHALL provide a new scope of `SUSPENSE_RESOLVING_KEY=True`
- **AND** components inside the inner Suspense SHALL see `True`
- **AND** after the inner Suspense completes, its scope SHALL be disposed
- **AND** components in the outer Suspense (outside the inner one) SHALL see the outer scope's `True` value

#### Scenario: Suspense DI scope is disposed on element removal before async resolution completes
- **WHEN** a `Suspense` element is removed from the DOM (e.g., via route change) while browser-side async resolution is still in progress
- **THEN** `_remove_element()` SHALL cancel the pending `asyncio.Task` via `task.cancel()` FIRST
- **AND** `_remove_element()` SHALL await the cancelled task (via `await task` wrapped in `try/except asyncio.CancelledError`) to ensure the task has fully terminated BEFORE disposing the scope
- **AND** only after the task is confirmed terminated, the DI scope with `SUSPENSE_RESOLVING_KEY=True` SHALL be disposed
- **AND** this ordering (cancel → await → dispose) guarantees the `_resolve()` callback cannot be executing when the scope is disposed

#### Scenario: Suspense boundary resolves async children before Component._render()
- **WHEN** an async component is a descendant of `SuspenseElement`
- **AND** `SuspenseElement._render()` is called
- **THEN** Suspense SHALL provide a DI-scoped flag (`SUSPENSE_RESOLVING_KEY: InjectKey[bool]`) set to `True`
- **AND** Suspense SHALL traverse the tree to find all `Component._pending_async_template` coroutines
- **AND** Suspense SHALL `await asyncio.gather(*coroutines)` to resolve them in parallel
- **AND** after resolution, Suspense SHALL call `Component._render()` on each resolved component
- **AND** `Component._render()` SHALL check `inject(SUSPENSE_RESOLVING_KEY)` and skip the await when `_pending_async_template` is already `None`
- **AND** fallback SHALL be replaced with children content

#### Scenario: Async component without Suspense resolves in own _render()
- **WHEN** an async component is NOT wrapped in a `Suspense` boundary
- **THEN** `Component._render()` SHALL await `_pending_async_template` directly
- **AND** `_pending_async_template` SHALL be set to `None` after resolution
- **AND** `__init_component()` SHALL be called with the resolved template

### Requirement: _pending_async_template observability window is safe for tree traversal

Between `__init__()` and the first `_render()`, the component is in an uninitialized state where `_tag_name`, `_attrs`, and `_children` are their `ElementBase` defaults (not yet set by `__init_component()`). Tree traversal code that detects pending async operations (e.g., `SuspenseElement` collecting coroutines) SHALL only read `_pending_async_template` and SHALL NOT access `_tag_name`, `_attrs`, `_children`, or `_property["template"]` on components with `_pending_async_template is not None`. Code accessing these fields during the observability window SHALL first check `_pending_async_template is None` as a guard.

#### Scenario: Suspense traversal during uninitialized window
- **WHEN** `SuspenseElement` traverses the element tree to detect pending async operations
- **AND** it encounters a component with `_pending_async_template is not None`
- **THEN** it SHALL collect the coroutine from `_pending_async_template`
- **AND** it SHALL NOT read `_tag_name`, `_attrs`, `_children`, or `_property["template"]`
- **AND** the traversal SHALL NOT raise `AttributeError` or `TypeError` due to uninitialized fields

#### Scenario: Non-Suspense traversal during uninitialized window
- **WHEN** any traversal code accesses `_tag_name`, `_attrs`, or `_children` on a component
- **AND** that component has `_pending_async_template is not None`
- **THEN** the accessed values SHALL be the `ElementBase` defaults (empty values)
- **AND** the code SHALL guard against uninitialized state by checking `_pending_async_template is None` before interpreting template-dependent fields

The `ComponentProperty` TypedDict SHALL type `template` as `ElementChildren | None`. When `None`, the component is in the unresolved async state. The value SHALL be resolved to `ElementChildren` before `__init_component()` is called. Sync components (those without `_pending_async_template`) always have `template` as `ElementChildren` (never `None`). Consumers that are only reached after `_render()` has completed (e.g., lifecycle hooks, child rendering loops) can safely assume `template is not None` — the `None` state is only observable during the brief window between `__init__()` and the first `_render()` for async components.

#### Scenario: ComponentProperty with None template
- **WHEN** an async component is created
- **THEN** `self._property["template"]` SHALL be `None`
- **AND** when `_render()` completes, `self._property["template"]` SHALL be the resolved `ElementChildren`

### Requirement: FuncComponentDef type shall accept async callables

The `FuncComponentDef` type alias SHALL accept both `Callable[[Context[Any]], ElementChildren]` and `Callable[[Context[Any]], Coroutine[Any, Any, ElementChildren]]`. The `define_component` decorator factory SHALL similarly accept both sync and async callables. The `__webcompy_component_definition__` attribute SHALL be set on async callables as it is on sync callables.

#### Scenario: Type checking an async component definition
- **WHEN** a developer writes `@define_component() async def MyComponent(context): ...`
- **THEN** the decorator SHALL accept the async callable without type errors
- **AND** the return type SHALL be `ComponentGenerator[PropsType]`

#### Scenario: _is_function_style_component_def with async definition
- **WHEN** `_is_function_style_component_def()` is called with an async component definition
- **THEN** it SHALL return `True` (it checks `callable()` and `__webcompy_component_definition__` attribute)
- **AND** the attribute check SHALL succeed regardless of whether the callable is sync or async

### Requirement: Context, lifecycle hooks, and DI scope shall work for async definitions

The active component context and effect scope SHALL be set up synchronously during `__setup__()` for both sync and async definitions. They SHALL be reset in the `finally` block after `component_def(context)` is called.

For **sync definitions**, lifecycle hooks (`on_before_rendering`, `on_after_rendering`, `on_before_destroy`), `_async_results`, and `_transferable_signals` SHALL be extracted from the Context during `__setup__()` after the body executes, as before.

For **async definitions**, the `Context` and `EffectScope` SHALL be bundled into a `ComponentRenderState` and saved on the `Component` instance during `__setup__()`. During `_render()`, the context and effect scope SHALL be re-activated via the `component_context()` context manager before the coroutine body is awaited. After the body resolves, lifecycle hooks, `_async_results`, and `_transferable_signals` SHALL be re-extracted from the Context to capture registrations made during async body execution. The re-extraction SHALL update `self._property["on_before_rendering"]` and `self._property["on_after_rendering"]` with the newly registered hooks.

The DI scope (`_active_di_scope`) is managed separately at the render-context level and SHALL remain available during `_render()` without being part of `ComponentRenderState`.

#### Scenario: Sync component hooks extracted during setup
- **WHEN** a sync component registers `context.on_before_rendering(fn)` during setup
- **THEN** the hook SHALL be extracted in `__setup__()` and stored in `self._property`
- **AND** the hook SHALL fire during `_render()` as before

#### Scenario: Async component context re-activated during render
- **WHEN** an async component's body calls `_active_component_context.get()` during `_render()`
- **THEN** the returned value SHALL be the component's `Context` instance (not `None`)
- **AND** composables relying on `_active_component_context` SHALL function correctly

#### Scenario: Async component effect scope re-activated during render
- **WHEN** an async component's body creates reactive effects during `_render()`
- **THEN** the effects SHALL be associated with the component's `EffectScope`
- **AND** the effects SHALL be cleaned up when the component is destroyed

#### Scenario: Composable-created effects tracked by component Effect scope
- **WHEN** a composable (e.g., `use_state()`, `use_async_result()`) creates reactive effects inside an async component's body during `_render()`
- **THEN** the effects SHALL be tracked by the component's `EffectScope` stored in `_render_state`
- **AND** the effects SHALL be cleaned up when the component is destroyed
- **AND** this SHALL satisfy the Effect scope requirements in `composables/spec.md`

#### Scenario: Async component hooks registered in body are captured
- **WHEN** an async component registers `context.on_before_rendering(fn)` inside the async body
- **THEN** after the body resolves, `__get_lifecyclehooks__()` SHALL return the registered hook
- **AND** `self._property["on_before_rendering"]` SHALL be updated with the hook
- **AND** the hook SHALL fire during subsequent rendering phases

#### Scenario: Async component async_results captured after body resolution
- **WHEN** an async component's body calls `use_async_result(fn)` during `_render()`
- **THEN** after the body resolves, `context._async_results` SHALL contain the registered AsyncResult
- **AND** `self._async_results` SHALL be updated with the new entries
- **AND** the AsyncResult SHALL be collected by `collect_transfer_data()`

#### Scenario: Sync component behavior unchanged
- **WHEN** a sync component is rendered
- **THEN** the context activation, hook extraction, and signal collection SHALL behave identically to before this change
- **AND** no `ComponentRenderState` re-activation SHALL occur during `_render()`

### Requirement: ComponentRenderState shall bundle render-time context

A `ComponentRenderState` dataclass SHALL be defined in `packages/webcompy/src/webcompy/components/_context_manager.py`. It SHALL contain `context: Context[Any]` and `effect_scope: EffectScope` fields. It MAY contain a `framework_cleanup: Callable[[], None]` field to centralize DI scope and EffectScope disposal. `Component.__setup__()` SHALL create a `ComponentRenderState` and store it on `self._render_state` for all components (sync and async). For sync components, `_render_state` SHALL be available but re-activation during `_render()` SHALL be a no-op (hooks already extracted). Sync components SHALL also use `component_context()` during `__setup__()` to ensure consistent ContextVar management, replacing the manual `set`/`reset` token pattern. For async components, `_render_state` SHALL be used to re-activate context and effect scope during `_render()`.

#### Scenario: ComponentRenderState is created during setup
- **WHEN** `Component.__setup__()` runs for any component
- **THEN** `self._render_state` SHALL be a `ComponentRenderState` instance
- **AND** `self._render_state.context` SHALL be the `Context` object
- **AND** `self._render_state.effect_scope` SHALL be the `EffectScope` created during setup

#### Scenario: ComponentRenderState available for re-activation
- **WHEN** `Component._render()` needs to re-activate context for an async component
- **THEN** `self._render_state` SHALL provide the `Context` and `EffectScope` needed for activation

### Requirement: component_context() shall centralize ContextVar activation

A `component_context(state: ComponentRenderState)` context manager SHALL be defined in `packages/webcompy/src/webcompy/components/_context_manager.py`. It SHALL activate `_active_component_context` and `_active_scope` upon entry and reset them upon exit (including on exception). The context manager SHALL be used in both `__setup__()` (for sync body execution) and `_render()` (for async body re-activation). Future ContextVars that need component-scoped activation SHALL be added to this single function.

#### Scenario: component_context activates and resets ContextVars
- **WHEN** `with component_context(state):` is entered
- **THEN** `_active_component_context.get()` SHALL return `state.context`
- **AND** `_active_scope.get()` SHALL return `state.effect_scope`
- **AND** upon exit, both SHALL be reset to their previous values

#### Scenario: component_context resets on exception
- **WHEN** an exception is raised inside a `with component_context(state):` block
- **THEN** the ContextVars SHALL be reset in the `finally` block
- **AND** the exception SHALL propagate to the caller

#### Scenario: Nested component_context calls work correctly
- **WHEN** a child component's `component_context()` is activated within a parent's activation scope
- **THEN** the child's ContextVars SHALL override the parent's within the child's `with` block
- **AND** upon the child's block exit, the parent's values SHALL be restored

### Requirement: Suspense SHALL activate component context during parallel coroutine resolution

When `SuspenseElement._render()` collects `_pending_async_template` coroutines and resolves them via `asyncio.gather()`, each coroutine SHALL be wrapped in an async helper that activates `component_context(component._render_state)` before awaiting. This ensures each async component body executes with its own context active, even during parallel resolution. Each wrapper is scheduled as a task by `asyncio.gather` (which creates task-local context copies), so concurrent coroutines do not interfere with each other's context.

After `asyncio.gather()` completes, `SuspenseElement._resolve_component_templates()` SHALL call `Component._refresh_async_setup_results()` for each resolved component before initializing its children. This re-extracts lifecycle hooks, `_async_results`, and `_transferable_signals` from each component's `Context`, as the body registrations occurred during the Suspense-managed resolution. `Component._render()` additionally guards re-extraction via `_async_setup_extracted` so the refresh occurs regardless of whether the temporary Suspense DI scope is still active.

#### Scenario: Suspense wraps coroutines with component context
- **WHEN** `SuspenseElement._render()` resolves async component coroutines via `asyncio.gather()`
- **THEN** each coroutine SHALL be wrapped with `component_context(component._render_state)`
- **AND** the body SHALL execute with `_active_component_context` set to the component's Context
- **AND** composables called inside the body SHALL function correctly

#### Scenario: Parallel resolution does not cross-contaminate contexts
- **WHEN** multiple async components are resolved in parallel by Suspense
- **THEN** each component's body SHALL see its own Context (not another component's)
- **AND** context isolation between concurrent coroutines SHALL be maintained

#### Scenario: Hooks captured after Suspense resolution
- **WHEN** an async component inside Suspense registers hooks during body execution
- **AND** `asyncio.gather()` completes
- **THEN** `SuspenseElement._resolve_component_templates()` SHALL re-extract hooks from the Context
- **AND** the hooks SHALL be available for the component's rendering phase

### Requirement: Error handling for failed async setup

If the `await self._pending_async_template` in `_render()` raises, the exception SHALL propagate through the async `_render()` chain. The effect scope and DI scope SHALL already be cleaned up (closed in `__setup__`'s `finally` block). The component SHALL remain uninitialized.

`_remove_element()` SHALL only be called if `__init_component()` was invoked before the failure. If `_pending_async_template` resolution fails before `__init_component()` was called, the component has no mounted DOM nodes and no initialized state — the component SHALL be removed from its parent's children list without calling `_remove_element()`, since there is nothing to clean up.

#### Scenario: Async setup raises an exception
- **WHEN** an async component's setup function raises (e.g., `await fetch()` throws)
- **THEN** the `try/except` block in `Component._render()` SHALL catch the exception
- **AND** if `__init_component()` was already called (e.g., failure happened after template resolution), `self._remove_element()` SHALL be called to clean up mounted DOM nodes
- **AND** if the failure occurred before `__init_component()` was called, the component SHALL be removed from its parent's children list without calling `_remove_element()` (no DOM nodes were mounted)
- **AND** the exception SHALL propagate to the caller of `_render()` for parent-level error handling
- **AND** the effect scope SHALL be disposed (from `__setup__`'s `finally`)
- **AND** the DI child scope SHALL be disposed (from `__setup__`'s `finally`)
- **AND** no resource leak SHALL occur
- **AND** no partially rendered nodes SHALL remain in the DOM

### Requirement: define_component decorator shall preserve async def

The `define_component` decorator factory SHALL set `__webcompy_component_definition__` on the callable and return a `ComponentGenerator` without wrapping the callable in a way that breaks `inspect.iscoroutinefunction()`. The original callable SHALL be stored in `ComponentGenerator._component_def` and called from `Component.__init__()`.

#### Scenario: define_component decorates an async function
- **WHEN** `@define_component()` decorates `async def MyComponent(context): ...`
- **THEN** `MyComponent.__webcompy_component_definition__` SHALL be `True`
- **AND** `inspect.iscoroutinefunction(MyComponent)` SHALL be `True`
- **AND** calling `MyComponent(props)` SHALL return a `Component` instance
- **AND** `ComponentGenerator._component_def` SHALL store the original async function
