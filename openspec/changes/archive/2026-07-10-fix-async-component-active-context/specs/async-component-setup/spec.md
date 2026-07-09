## MODIFIED Requirements

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

<!-- Replaces base spec Scenario: Async component with lifecycle hooks (hooks are NOT captured during __setup__() for async defs; they are re-extracted after body resolution) -->
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

## ADDED Requirements

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
