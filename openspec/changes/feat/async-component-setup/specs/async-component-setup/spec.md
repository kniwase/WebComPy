# Async Component Setup

## Purpose

Component setup functions may be `async def`, enabling developers to `await` async operations (API calls, async resource loading) during component initialization. The coroutine is resolved during the async `_render()` phase, making the fetched data available for the initial render. Synchronous component definitions continue to work unchanged — `inspect.iscoroutinefunction()` transparently detects async definitions and uses a two-phase initialization strategy.

## Requirements

### Requirement: Component setup functions may be async def

A component definition decorated with `@define_component` SHALL be `async def`. The async keyword SHALL be detected via `inspect.iscoroutinefunction()`, and the resulting coroutine SHALL be stored and resolved during `_render()`. Synchronous definitions SHALL be initialized immediately as before.

#### Scenario: Defining an async component
- **WHEN** a developer writes `@define_component async def MyComponent(context): ... return html.DIV({}, "hello")`
- **THEN** the component SHALL be created without error
- **AND** `MyComponent(props)` SHALL return a `Component` instance
- **AND** the component SHALL render correctly when `_render()` is awaited

#### Scenario: Awaiting an async operation during setup
- **WHEN** a developer writes:
  ```python
  @define_component
  async def MyComponent(context):
      data = await fetch("/api/data")
      return html.DIV({}, str(data))
  ```
- **THEN** `await fetch("/api/data")` SHALL execute on the event loop during `_render()`
- **AND** the resolved `data` SHALL be available when the template is rendered
- **AND** the component SHALL render the fetched data in the DOM

#### Scenario: Sync component continues to work unchanged
- **WHEN** a developer writes `@define_component def MyComponent(context): return html.DIV({}, "hello")`
- **THEN** the component SHALL initialize immediately in `__init__()`
- **AND** behavior SHALL be identical to pre-async-component-setup

### Requirement: Two-phase initialization for async components

When a component definition is `async def`, initialization SHALL be split into two phases: (1) during `__init__()`, the coroutine is stored in `self._pending_async_template` and `__init_component()` is skipped; (2) during the first `_render()`, the coroutine is awaited, the template is resolved, and `__init_component()` is called to finish initialization.

#### Scenario: Async component initialization deferred to render
- **WHEN** an async component is created via `MyComponent(props)`
- **THEN** `self._pending_async_template` SHALL contain the unresolved coroutine
- **AND** `self.__init_component()` SHALL NOT be called during `__init__()`
- **AND** the component's `_tag_name`, `_attrs`, and `_children` SHALL be uninitialized (defaults from `ElementBase`)

#### Scenario: Async component resolved during render
- **WHEN** `_render()` is called on an async component with `self._pending_async_template` set
- **THEN** the coroutine SHALL be awaited to obtain the resolved template
- **AND** `self._pending_async_template` SHALL be set to `None`
- **AND** `self.__init_component()` SHALL be called with the resolved template
- **AND** the component SHALL then proceed with normal async rendering (lifecycle hooks, child rendering)

#### Scenario: Async component renders only once
- **WHEN** `_render()` is called on an already-resolved async component (second+ render, e.g., after a reactive update)
- **THEN** `self._pending_async_template` SHALL be `None`
- **AND** the component SHALL skip the two-phase init block
- **AND** the component SHALL proceed directly to normal rendering

### Requirement: ComponentProperty template shall be nullable

The `ComponentProperty` TypedDict SHALL type `template` as `ElementChildren | None`. When `None`, the component is in the unresolved async state. The value SHALL be resolved to `ElementChildren` before `__init_component()` is called.

#### Scenario: ComponentProperty with None template
- **WHEN** an async component is created
- **THEN** `self._property["template"]` SHALL be `None`
- **AND** when `_render()` completes, `self._property["template"]` SHALL be the resolved `ElementChildren`

### Requirement: FuncComponentDef type shall accept async callables

The `FuncComponentDef` type alias SHALL accept both `Callable[[Context[Any]], ElementChildren]` and `Callable[[Context[Any]], Coroutine[Any, Any, ElementChildren]]`. The `define_component` decorator SHALL similarly accept both sync and async callables. The `__webcompy_component_definition__` attribute SHALL be set on async callables as it is on sync callables.

#### Scenario: Type checking an async component definition
- **WHEN** a developer writes `@define_component async def MyComponent(context): ...`
- **THEN** the decorator SHALL accept the async callable without type errors
- **AND** the return type SHALL be `ComponentGenerator[PropsType]`

#### Scenario: _is_function_style_component_def with async definition
- **WHEN** `_is_function_style_component_def()` is called with an async component definition
- **THEN** it SHALL return `True` (it checks `callable()` and `__webcompy_component_definition__` attribute)
- **AND** the attribute check SHALL succeed regardless of whether the callable is sync or async

### Requirement: Context, lifecycle hooks, and DI scope shall work for async definitions

The active component context, effect scope, and DI scope SHALL be set up synchronously during `__setup__()` for both sync and async definitions. They SHALL be reset in the `finally` block after `component_def(context)` is called synchronously to obtain the coroutine. Lifecycle hooks (`on_before_rendering`, `on_after_rendering`, `on_before_destroy`) SHALL be registered during `__setup__()` and invoked during `_render()`/destruction as with sync definitions.

#### Scenario: Async component with lifecycle hooks
- **WHEN** an async component registers `@on_after_rendering` during setup
- **THEN** the hook SHALL be registered normally during `__setup__()`
- **AND** the hook SHALL fire after the component renders (including after async template resolution)

#### Scenario: Async component with DI provide
- **WHEN** an async component calls `context.provide(SomeKey, value)` during setup
- **THEN** the DI child scope SHALL be created synchronously during `__setup__()`
- **AND** the provided value SHALL be available to descendant components

### Requirement: Error handling for failed async setup

If the `await self._pending_async_template` in `_render()` raises, the exception SHALL propagate through the async `_render()` chain. The effect scope and DI scope SHALL already be cleaned up (closed in `__setup__`'s `finally` block). The component SHALL remain uninitialized.

#### Scenario: Async setup raises an exception
- **WHEN** an async component's setup function raises (e.g., `await fetch()` throws)
- **THEN** the exception SHALL propagate to the caller of `_render()`
- **AND** the effect scope SHALL be disposed (from `__setup__`'s `finally`)
- **AND** the DI child scope SHALL be disposed (from `__setup__`'s `finally`)
- **AND** no resource leak SHALL occur

### Requirement: define_component decorator shall preserve async def

The `define_component` decorator SHALL set `__webcompy_component_definition__` on the callable and return a `ComponentGenerator` without wrapping the callable in a way that breaks `inspect.iscoroutinefunction()`. The original callable SHALL be stored in `ComponentGenerator._component_def` and called from `Component.__init__()`.

#### Scenario: define_component decorates an async function
- **WHEN** `@define_component` decorates `async def MyComponent(context): ...`
- **THEN** `MyComponent.__webcompy_component_definition__` SHALL be `True`
- **AND** `inspect.iscoroutinefunction(MyComponent)` SHALL be `True`
- **AND** calling `MyComponent(props)` SHALL return a `Component` instance
- **AND** `ComponentGenerator._component_def` SHALL store the original async function
