## Why

WebComPy supports two component definition styles — function-style (`@define_component`) and class-style (`@component_class`) — that produce the same output but require separate internal implementations (two Context protocols, two instantiation paths, two lifecycle registration APIs, and separate decorator sets). Over 85% of production code uses the function style, yet the framework maintains both paths indefinitely. This dual implementation doubles maintenance surface, blocks future extensibility (DI/provide-inject, plugins), and forces class-style users into Python-idiomatic awkwardness (`__new__` prohibition, `__init_subclass__` for IDs). Meanwhile, the function style suffers from callback nesting depth that makes complex components harder to read — lifecycle hooks are registered imperatively via `ctx.on_after_rendering(func)`, and async patterns require stacking `@AsyncWrapper()` + `@context.on_after_rendering` decorators.

## What Changes

- **Add standalone lifecycle decorators**: `@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy` as module-level decorators that use `contextvars.ContextVar` to register hooks without requiring an explicit `context` argument. The existing `context.on_xxx()` methods remain functional for backward compatibility.
- **Add `useAsyncResult` composable**: A new `AsyncResult[T]` class and `useAsyncResult()` function that encapsulates async state management (PENDING / LOADING / SUCCESS / ERROR), result caching (SWR pattern), and error handling — replacing the common `@AsyncWrapper()` + `@context.on_after_rendering` pattern. Includes `default` parameter to eliminate `T | None` ambiguity, `watch` parameter for reactive-driven refetching, and `immediate` parameter for manual trigger control.
- **Add `useAsync` composable**: A lightweight side-effect-only wrapper that executes an async function after rendering, replacing the `@AsyncWrapper()` + `@context.on_after_rendering` combo for fire-and-forget patterns.
- **Deprecate `context.on_xxx()` methods**: The imperative registration pattern (`context.on_after_rendering(func)`) becomes a secondary API. Standalone decorators are preferred.
- **Deprecate class-style component API**: `@component_class`, `ComponentAbstract`, `TypedComponentBase`, `NonPropsComponentBase`, and class-style decorators (`@component_template`, `@on_before_rendering`, etc. on class methods) are deprecated. Removal will happen in a subsequent change.

## Capabilities

### New Capabilities
- `composables`: Composition functions (`useAsync`, `useAsyncResult`) and standalone lifecycle hooks (`@on_before_rendering`, `@on_after_rendering`, `@on_before_destroy`, `useTitle`, `useMeta`) for encapsulating and reusing stateful logic within function-style components.

### Modified Capabilities
- `components`: Deprecate class-style component definition. Add ContextVar-based standalone lifecycle hooks as the preferred API alongside existing `context.on_xxx()` methods.
- `async`: Add `AsyncResult` reactive container with structured loading/success/error states, SWR-style data caching, `watch`-driven refetch, and `default` parameter. Deprecate `AsyncComputed` in favor of `useAsyncResult`.

## Impact

- **`webcompy/components/`**: Add `_hooks.py` (ContextVar + standalone decorators + composable functions). Modify `_component.py` to set/reset ContextVar around function-style setup. Deprecate `_abstract.py` and `_decorators.py`.
- **`webcompy/aio/`**: Add `_async_result.py` (`AsyncResult`, `AsyncState`, `useAsyncResult`, `useAsync`). Update `__init__.py` exports.
- **`webcompy/components/_libs.py`**: Add `ComponentContext.on_xxx` backward compatibility (no change needed — existing methods continue to work). Add `ContextVar` import and accessor.
- **Existing code**: All existing function-style components continue working unchanged. Class-style components continue working but emit deprecation warnings. Migration guide needed.
- **Tests**: Add unit tests for `AsyncResult` (pure state machine), `useAsyncResult` (ContextVar hook registration), and standalone lifecycle decorators. Existing E2E tests continue passing.

## Known Issues Addressed

- AsyncComputed.value is T | None — no way to distinguish "not yet resolved" from "resolved to None" without checking done flag → `AsyncResult` introduces explicit `AsyncState` enum (`PENDING`, `LOADING`, `SUCCESS`, `ERROR`) with `is_loading` / `is_success` / `is_error` computed booleans and `default` parameter to eliminate `None` ambiguity.
- AsyncComputed._error sets _done = False on error, conflating error state with pending state → `AsyncResult.state` uses `AsyncState.ERROR` as a distinct state.
- No provide/inject (DI) system → The `ContextVar` mechanism introduced for standalone hooks is the foundation for a future DI/provide-inject system.

## Non-goals

- Removing class-style components entirely in this change (only deprecation).
- Removing `AsyncWrapper` or `AsyncComputed` (only deprecation in favor of new APIs).
- Adding `useAsyncResultAll` (parallel composition) — deferred to a future change.
- Adding `useDebounced` or similar timing composables — deferred to a future change.
- SSG-side data fetching capability for `HttpClient`.
- Plugin system or provide/inject (the ContextVar infrastructure enables these but they are out of scope).