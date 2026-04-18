## Context

WebComPy currently has two async primitives for reactive async state:

1. **`AsyncComputed`** (`webcompy/aio/_aio.py`): A `SignalBase[T | None]` subclass that accepts a coroutine, resolves it once, and exposes `value`, `done`, and `error` properties. It has two design flaws: (a) `value` is `T | None`, making it impossible to distinguish "pending" from "resolved to None"; (b) `_error` sets `_done = False`, conflating error state with pending state. It has zero usage in the codebase — no internal code, no user-facing code, no tests.

2. **`AsyncResult`** (`webcompy/aio/_async_result.py`): A standalone class (not a `SignalBase`) that exposes `state: Signal[AsyncState]`, `data: Signal[T | None]`, `error: Signal[Exception | None]`, and four `Computed[bool]` predicates. It solves both `AsyncComputed` flaws with an explicit state machine, a `default` parameter, SWR-style data preservation on error, and `refetch()` for re-execution.

Additionally, `AsyncWrapper` provides fire-and-forget async dispatching (no result tracking), and `resolve_async` is the low-level coroutine dispatcher. Both are orthogonal to `AsyncComputed` and remain unchanged.

The existing `async` spec already describes `AsyncResult` and `useAsyncResult` as the primary API. The `overview` spec still references `AsyncComputed` in one scenario.

## Goals / Non-Goals

**Goals:**
- Remove `AsyncComputed` class and its public export
- Update specs to reflect `AsyncResult`/`useAsyncResult` as the sole async state primitive
- Remove the two resolved known issues from `openspec/config.yaml`
- Provide a clear migration path for any hypothetical external users

**Non-Goals:**
- Refactoring `AsyncWrapper` or `resolve_async` (different use case)
- Adding new `AsyncResult` features (already meets all requirements)
- Renaming `ReactiveList`/`ReactiveDict` (orthogonal concern)
- Changing `useAsyncResult` or `useAsync` hooks
- Making `AsyncResult` inherit from `SignalBase` (the `.data` accessor pattern is sufficient)

## Decisions

### Decision 1: Remove `AsyncComputed` entirely rather than deprecating

**Choice**: Full removal  
**Alternatives considered**:
- Deprecation warning + `__getattr__` redirect: Adds maintenance burden for a class with zero known users. A deprecation period only makes sense if there are active consumers to migrate.
- Keep `AsyncComputed` but fix its bugs: Doesn't solve the fundamental `T | None` type ambiguity — `AsyncResult`'s `AsyncState` enum is the right solution and would require duplicating state machine logic.

**Rationale**: Zero usage in the codebase means zero migration burden. The class is buggy by design (state conflation), and `AsyncResult` is a strict superset in capability. Keeping two async state primitives creates confusion about which to use.

### Decision 2: No changes to `AsyncResult` API

**Choice**: Leave `AsyncResult` as-is  
**Alternatives considered**:
- Make `AsyncResult` inherit from `SignalBase`: Would allow `html.SPAN({}, result)` instead of `html.SPAN({}, result.data)`. However, `AsyncResult` has `state`, `data`, and `error` as separate signals — making it a `SignalBase` would require choosing one (likely `data`), introducing conceptual confusion about which value the signal represents.
- Add `__value__` property as alias for `.data`: Unnecessary indirection. The `.data` accessor is clear and explicit.

**Rationale**: The current `AsyncResult` design uses three separate signals (`state`, `data`, `error`) because async operations have three distinct dimensions of reactivity. Merging them into one signal would lose granularity.

### Decision 3: Update overview spec scenario to reference `useAsyncResult`

**Choice**: Replace `AsyncComputed` mention with `useAsyncResult`  
**Rationale**: The existing `async` spec already fully describes `AsyncResult` and `useAsyncResult`. The `overview` spec has a single scenario mentioning `AsyncComputed` that needs updating to reference the current API.

## Risks / Trade-offs

- **[Breaking change for external consumers]** → Any user code importing `AsyncComputed` will break. Mitigation: zero usage in codebase, and `AsyncResult` provides strictly better semantics. The migration is straightforward: replace `AsyncComputed(coroutine())` with `AsyncResult(func)` where `func` returns the coroutine.
- **[Loss of SignalBase integration]** → `AsyncComputed` was directly usable as a signal in templates. `AsyncResult.data` is a `Signal` but adds one level of indirection. Mitigation: the dominant pattern is `switch(cases=[(result.is_loading, ...), (result.is_success, ...)])`, which is clearer than checking `done`/`error` properties. Direct value display can use `result.data`.
- **[Overview spec reference]** → The scenario must correctly describe `useAsyncResult` behavior. The async spec already covers this comprehensively.

## Migration Plan

1. Remove `AsyncComputed` class from `webcompy/aio/_aio.py`
2. Remove `AsyncComputed` from `webcompy/aio/__init__.py` exports
3. Update `overview` spec
4. Remove resolved known issues from `openspec/config.yaml`
5. Run lint, typecheck, and tests

**Rollback**: Restore the `AsyncComputed` class and export (single commit revert).

**Migration guide for users** (if any):
```python
# Before (AsyncComputed):
result = AsyncComputed(fetch_data())
if result.done:
    value = result.value

# After (AsyncResult):
result = AsyncResult(fetch_data)
result.refetch()
if result.state.value == AsyncState.SUCCESS:
    value = result.data.value

# Or in a component:
result = useAsyncResult(fetch_data, default=[], immediate=True)
```