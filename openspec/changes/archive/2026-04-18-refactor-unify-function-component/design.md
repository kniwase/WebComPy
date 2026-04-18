## Context

WebComPy currently maintains two component definition styles that share a single output type (`ComponentGenerator`) but differ in their input path: function-style (`@define_component`) uses `Context` with imperative lifecycle registration, while class-style (`@component_class`) uses `ComponentAbstract` with decorator-based method marking. The internal `_component.py.__setup` branches between these two paths. The function style is used in ~85% of production code but suffers from nesting depth when combining lifecycle hooks with async operations. The class style's implementation relies on patterns alien to Python (`__new__` prohibition, `__init_subclass__` for ID generation) and blocks future extensibility (no way to inject shared logic without inheritance).

The reactive system has `AsyncComputed` with a `T | None` value type that conflates "pending" and "resolved to None", and an `_error`/`_done` state machine that conflates error and pending states. No structured loading/success/error state exists.

## Goals / Non-Goals

**Goals:**
- Introduce standalone lifecycle decorators that work inside function-style components without requiring explicit `context` argument
- Introduce `AsyncResult` and `useAsyncResult` composable to replace the common `@AsyncWrapper()` + `ctx.on_after_rendering` pattern with structured state management
- Introduce `useAsync` composable for fire-and-forget async operations after rendering
- Establish `contextvars.ContextVar` as the mechanism for implicit context access, enabling future composable extensibility
- Separate `AsyncResult` (pure state machine, testable without ContextVar) from `useAsyncResult` (ContextVar-aware thin adapter)
- Provide a clear deprecation path for class-style components and `context.on_xxx()` APIs
- Maintain zero breaking changes for existing function-style components

**Non-Goals:**
- Removing class-style components (deprecation only in this change)
- Removing `AsyncWrapper` or `AsyncComputed` (deprecation only)
- Adding `useAsyncResultAll` (parallel composition helper — deferred)
- Adding `useDebounced` or other timing composables (deferred)
- Adding provide/inject or plugin system (ContextVar enables but does not implement)
- SSG-side data fetching for HttpClient

## Decisions

### D1: ContextVar for implicit component context

**Decision**: Use `contextvars.ContextVar` to track the active `Context` object during component setup, allowing standalone functions to access it without a parameter.

**Alternatives considered**:
- *Keep context explicit*: Maintains Python's "explicit is better" philosophy but perpetuates the nesting problem and makes composables impossible (a composable can't thread `context` through nested function calls without explicit parameter passing at every level).
- *Global variable*: Thread-unsafe, breaks under concurrent usage. PyScript is single-threaded but SSG uses asyncio event loops.

**Rationale**: Vue 3 Composition API uses exactly this pattern (`getCurrentInstance()` is ContextVar-equivalent). The single-threaded execution model in both browser (PyScript) and server (asyncio) makes ContextVar safe. Token-based reset ensures correct nesting when child components are instantiated inside parent setup.

### D2: Standalone lifecycle decorators shadow context methods

**Decision**: `@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy` are module-level decorators that read ContextVar. They are the preferred API; `context.on_xxx()` remains functional but deprecated.

**Alternatives considered**:
- *Remove context.on_xxx immediately*: Breaking change, not acceptable for existing code.
- *Redirect context.on_xxx to ContextVar internally*: Possible but adds indirection. Keep both working independently.

**Rationale**: The decorator form eliminates `ctx.on_after_rendering(func)` nesting and aligns with the class-style decorator pattern developers already know. Both APIs register to the same `Context` internal state, so they are interchangeable.

### D3: AsyncResult is Context-free, useAsyncResult is the adapter

**Decision**: `AsyncResult` is a pure state machine that knows nothing about component lifecycle. `useAsyncResult` wraps it by connecting lifecycle hooks (`on_after_rendering` for immediate execution, `on_before_destroy` for cleanup, reactive `watch` for automatic refetching).

**Alternatives considered**:
- *Merge everything into AsyncResult*: Makes it untestable outside component context. Creates a god object.
- *No separation, only useAsyncResult*: Same problem — cannot test state transitions without ContextVar.

**Rationale**: Separation follows the principle of testability. `AsyncResult` can be tested with plain `asyncio.run()` and `Reactive` assertions. `useAsyncResult` is a thin 15-line adapter that only needs ContextVar tests for registration correctness.

### D4: AsyncState enum with computed boolean predicates

**Decision**: `AsyncResult.state` is `Reactive[AsyncState]` where `AsyncState` is an enum with `PENDING`, `LOADING`, `SUCCESS`, `ERROR`. `is_loading`, `is_success`, `is_error`, `is_pending` are `Computed[bool]` derived from state.

**Alternatives considered**:
- *Three separate Reactive booleans*: Fragile — nothing prevents inconsistent combinations like `is_loading=True, is_success=True`.
- *Tagged union (AsyncResult type)*: Type-safe in theory but incompatible with `switch()` element which requires `Reactive[bool]` case conditions.

**Rationale**: Enum + Computed ensures consistency by construction. The Computed booleans plug directly into `switch()` case conditions. This matches how developers already use `Reactive[bool]` with `switch()` in existing components.

### D5: SWR-style data caching with `default` parameter

**Decision**: `AsyncResult.data` is `Reactive[T | None]` by default. When `default` is provided, initial value is `default` and `data` preserves the last successful value during refetch (`data` is never reset to `None` after initial success).

**Alternatives considered**:
- *Always `T | None`, force switch() protection*: Forces all consumers into switch blocks even for simple lists. Boilerplate-heavy.
- *Separate `value` (T|None) and `data` (T with default)*: Confusing to have two similar properties.

**Rationale**: The `default` parameter lets developers opt into type-safe `T` (e.g., `default=[]` for list data used with `repeat()`). Without `default`, the `T | None` flow is protected by `switch()` and `is_success` checks. SWR data preservation (not clearing `data` on refetch) is the modern standard (React SWR, VueUse, Solid) and avoids UI flicker.

### D6: `watch` parameter for reactive-driven refetching

**Decision**: `useAsyncResult` accepts `watch: Iterable[ReactiveBase[Any]]`. Each `ReactiveBase` in the list gets `on_after_updating` registered to call `refetch()`. Callbacks are cleaned up via `on_before_destroy`.

**Alternatives considered**:
- *No watch, manual on_after_updating*: Forces users to write boilerplate `query.on_after_updating(lambda _: result.refetch())` + cleanup.
- *watch as a dict of parameter names*: Overcomplicates the API. The `func` closure already captures Reactives.

**Rationale**: `watch` declaratively expresses "which Reactives drive refetching" without boilerplate. The closure pattern (`lambda: fetch(url.value)`) already handles parameterization, so `watch` only needs to specify triggers.

### D7: Class-style deprecation strategy

**Decision**: Add `DeprecationWarning` to `ComponentAbstract.__init_subclass__`, `@component_template`, `@component_class`, and `ClassStyleComponentContenxt`. No removal in this change.

**Rationale**: Class-style components are used in 9+ places. Deprecation gives users time to migrate. A future change will remove the class-style path entirely and delete `_abstract.py`, `_decorators.py`, and the class branch in `_component.py.__setup`.

## Risks / Trade-offs

- **[ContextVar implicit context]** Python's "explicit is better than implicit" philosophy is violated. → Mitigation: `LookupError` at call time if used outside a setup function. Clear error message. Only lifecycle hooks use implicit context; `props` and `slots()` remain explicit on `context`.

- **[ContextVar nesting with child components]** When a parent component instantiates a child inside setup, the child's `Component.__setup` sets its own ContextVar, masking the parent's. → Mitigation: Token-based reset (`contextvars.copy_context()` or manual `set`/`reset` pairs) ensures correct restoration. The existing code in `_component.py.__setup` already creates a new `Context` per component.

- **[AsyncResult refetch is sync up to aio_run, then async]** On the server side, `refetch()` calls `asyncio.run()` which blocks until completion. This means test assertions can follow `refetch()` immediately. In the browser, `asyncio.ensure_future()` is non-blocking. → Mitigation: This matches the existing `resolve_async`/`AsyncWrapper` behavior. E2E tests handle the browser case.

- **[watch callbacks leaked if component destroyed without on_before_destroy]** The `on_before_destroy` hook registered by `useAsyncResult` must fire for cleanup. If `Component._remove_element` is bypassed, callbacks leak. → Mitigation: `Component._remove_element` is the only destruction path in normal usage. The existing `_purge_reactive_members__` no-op issue is a separate known issue.

- **[Deprecation noise]** 9+ class-style usages will emit `DeprecationWarning` on import/class-definition. → Mitigation: Use `warnings.warn(..., stacklevel=2)` to point at the user's code. Future change includes migration script.

## Open Questions

- Should `useTitle()` and `useMeta()` composables be included in this change or deferred? They are simple wrappers (`on_after_rendering(lambda: context.set_title(...))`) but add API surface.
- The exact module path: `webcompy.composables` vs `webcompy.hooks` vs importing directly into `webcompy.components`. The ContextVar and composables need a home.
- Whether `useAsyncResult` should also register an `on_before_destroy` that cancels in-flight async operations (not just cleanup `watch` callbacks). This depends on whether `asyncio.Task` cancellation is safe in PyScript.