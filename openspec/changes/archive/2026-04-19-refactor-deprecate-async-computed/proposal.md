## Why

`AsyncComputed` has two design flaws that make it unreliable: (1) `value` is typed `T | None`, making it impossible to distinguish "pending" from "resolved to None" at the type level, and (2) the `_error` callback sets `_done = False`, conflating the error state with the pending state. The newer `AsyncResult` class solves both problems with an explicit `AsyncState` enum (`PENDING`, `LOADING`, `SUCCESS`, `ERROR`), a `default` parameter for typed initial values, SWR-style stale data preservation, and `refetch()` for re-execution. `AsyncComputed` has zero usage in the codebase (no user code, no internal code, no tests). It should be removed to eliminate the buggy API surface and the confusing coexistence of two async primitives.

## What Changes

- **BREAKING**: Remove the `AsyncComputed` class from `webcompy.aio`
- Remove `AsyncComputed` from `webcompy/aio/__init__.py` exports
- Remove `AsyncComputed` references from `overview` spec
- Remove the two Async-related known issues from `openspec/config.yaml` (they are solved by `AsyncResult`)

## Capabilities

### New Capabilities

_None_

### Modified Capabilities

- `overview`: Remove `AsyncComputed` mention from the async requirement scenario, replace with `AsyncResult`/`useAsyncResult`
- `async`: Update spec to reflect that `AsyncResult` and `useAsyncResult` are the sole async primitives (remove `AsyncComputed` existence assumption)

## Impact

- **Public API**: `AsyncComputed` removed from `webcompy.aio` — breaking change for any external consumer using it. Since there are zero known usages, impact is negligible.
- **Specs**: `overview` and `async` specs updated to remove `AsyncComputed` references.
- **Config**: Two known issues under "Async" in `openspec/config.yaml` removed (resolved by this change).
- **No code changes beyond removal**: `AsyncResult`, `AsyncWrapper`, `resolve_async`, `useAsyncResult`, `useAsync` all remain unchanged.

## Known Issues Addressed

- AsyncComputed.value is T | None — no way to distinguish "not yet resolved" from "resolved to None" without checking done flag → Removed; `AsyncResult` provides `AsyncState` enum and `default` parameter.
- AsyncComputed._error sets _done = False on error, conflating error state with pending state → Removed; `AsyncResult` uses `AsyncState.ERROR` as a distinct state.

## Non-goals

- Refactoring `AsyncWrapper` or `resolve_async` — these serve different use cases (fire-and-forget, low-level dispatching) and remain unchanged.
- Adding new `AsyncResult` features — the class already meets all requirements.
- Renaming `ReactiveList`/`ReactiveDict` to match the `Signal` naming convention — out of scope.