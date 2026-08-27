## MODIFIED Requirements

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

### Requirement: define_component decorator shall preserve async def

The `define_component` decorator factory SHALL set `__webcompy_component_definition__` on the callable and return a `ComponentGenerator` without wrapping the callable in a way that breaks `inspect.iscoroutinefunction()`. The original callable SHALL be stored in `ComponentGenerator._component_def` and called from `Component.__init__()`.

#### Scenario: define_component decorates an async function
- **WHEN** `@define_component()` decorates `async def MyComponent(context): ...`
- **THEN** `MyComponent.__webcompy_component_definition__` SHALL be `True`
- **AND** `inspect.iscoroutinefunction(MyComponent)` SHALL be `True`
- **AND** calling `MyComponent(props)` SHALL return a `Component` instance
- **AND** `ComponentGenerator._component_def` SHALL store the original async function
