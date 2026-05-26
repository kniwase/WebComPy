# Design: Async Component Setup

## Problem

`Component.__init__()` calls `__setup()` which executes the component definition function. If the definition is `async def`, calling it returns a coroutine, not a template. Python's `__init__` cannot be `async`, so we cannot `await` the coroutine during construction. A two-phase init strategy is needed: store the coroutine at init time, resolve it during the first async `_render()`.

## Decisions

### Decision 1: Two-phase initialization

**Chosen**: `Component.__init__()` detects async definitions and defers `__init_component()` to `_render()`.

**Phase 1 — `__init__`**:
```python
def __init__(self, component_def, props, slots):
    self._instance_id = uuid4()
    self._attrs = {}
    self._event_handlers = {}
    self._ref = None
    self._children = []
    self._head_props = None
    self._pending_async_template = None
    super().__init__()
    property = self.__setup(component_def, props, slots)
    if self._pending_async_template is None:
        self.__init_component(property)
```

**Phase 2 — `_render()`**:
```python
async def _render(self):
    if self._pending_async_template is not None:
        template = await self._pending_async_template
        self._pending_async_template = None
        property = self._property
        property["template"] = template
        self.__init_component(property)
    # ... normal async render flow ...
```

**Rationale**: This is the only viable pattern — `__init__` cannot await. The two-phase pattern is well established (e.g., `__init__` + `__await__` in asyncio-friendly classes, or lazy initialization). Since `_render()` is already async (from `feat/async-rendering-pipeline`), awaiting the coroutine there is natural.

**Rejected alternative**: Using `asyncio.run()` in `__init__` — this would create a new event loop on the server and fail in the browser where PyScript manages the loop.

### Decision 2: Detection via `inspect.iscoroutinefunction()`

**Chosen**: In `__setup__()`, check `inspect.iscoroutinefunction(component_def)` before calling it. If true, call it to get the coroutine, store in `self._pending_async_template`, set `template = None`. If false, call it and use the result directly.

```python
try:
    if iscoroutinefunction(component_def):
        coro = component_def(context)
        self._pending_async_template = coro
        template = None
    else:
        template = component_def(context)
finally:
    # ... existing context/di resets ...
```

**Rationale**: Checking the function type before calling it avoids needing to inspect the return value. `iscoroutinefunction()` is a well-known Python stdlib function in `inspect`. The alternative — calling the function and checking `inspect.iscoroutine(result)` — would also work but is less explicit.

### Decision 3: `ComponentProperty` template becomes nullable

**Chosen**: `ComponentProperty["template"]` type changes from `ElementChildren` to `ElementChildren | None`. When None, the component is in the unresolved async state.

**Rationale**: The template field holds `None` between `__init__` and the first `_render()` for async components. This accurately reflects the state. The `Component._render()` method resolves and replaces it before `__init_component()` is called, so no other code sees the `None` value.

### Decision 4: `FuncComponentDef` type alias broadened

**Chosen**: The type alias expands to accept async callables:
```python
FuncComponentDef: TypeAlias = (
    Callable[[Context[Any]], ElementChildren]
    | Callable[[Context[Any]], Coroutine[Any, Any, ElementChildren]]
)
```

Same change in `_generator.py` for the `define_component` parameter type.

**Rationale**: This reflects the real possibility of async component definitions. The `_is_function_style_component_def()` guard already checks `callable()` and `__webcompy_component_definition__` attribute — it doesn't care about the return type, so it needs no change.

### Decision 5: No changes to `Component.__setup__()` hook/DI/scope logic

**Chosen**: The DI scope setup, effect scope creation, context management, and lifecycle hook extraction in `__setup__()` are unchanged. Only the `template = component_def(context)` line is wrapped in the async detection branch.

**Rationale**: All the context machinery (DI scope, effect scope, lifecycle hooks) works the same for async definitions — they're set up during `__init__` synchronously and cleaned up in the `finally` block. Only the template resolution is deferred.

## No changes to

- `_generator.py`'s `ComponentStore` — registration is name-based, not affected by async
- `_generator.py`'s scoped CSS logic — independent of template resolution
- `_hooks.py` — lifecycle decorators already accept any callable
- DI subsystem — scope creation/destruction is unchanged
- App/SSG/CLI layers — they already call async `_render()`

## Risks / Trade-offs

- **Uninitialized component window**: Between `__init__` and first `_render()`, the component's `_tag_name`, `_attrs`, and `_children` are uninitialized (inherited from `ElementBase` defaults). No code should query these before `_render()` completes, which is already the contract — `_render()` is always called before any DOM interaction.
- **Error during async setup**: If `await coro` in `_render()` raises, the component remains uninitialized. The exception propagates through the async `_render()` chain. The effect scope and DI scope are already cleaned up (they were closed in `__setup__`'s `finally` block), so there's no resource leak. The component's element node may be partially mounted; the error handling responsibility lies with the caller (app/SSG).
