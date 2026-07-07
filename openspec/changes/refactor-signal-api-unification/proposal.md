## Why

Phase 2 (`feat-signal-composable`) introduced `signal()` as the recommended signal creation API and added `UserWarning` to `Signal()` direct construction. However, the framework still has inconsistencies: `Reactive` may exist as an alias for `Signal`, `Computed()` class constructor may coexist with `computed()`, and internal framework code still uses `Signal()` / `Signal._create()` directly. This change completes the unification by making function-style creation (`signal()`, `computed()`) the sole recommended API across all reactive primitives, escalating the deprecation level, and cleaning up internal usage.

This change depends on `feat-signal-composable` (Phase 2) and may incorporate `investigate-reactive-collections` (Phase 3a) findings if the investigation recommends deprecating `ReactiveList` / `ReactiveDict`.

## What Changes

- Escalate `Signal()` direct construction warning from `UserWarning` to `DeprecationWarning` (the class will eventually be removed as a public constructor)
- Remove or deprecate the `Reactive` alias for `Signal` (if one exists) — `signal()` is the unified creation API
- Ensure `computed()` is the sole recommended way to create `Computed` instances; deprecate `Computed()` class constructor if it exists as a separate callable
- Migrate all internal framework code from `Signal()` / `Signal._create()` to `signal()` where transfer is needed, or keep `Signal._create()` only for truly internal non-transfer contexts
- Update type stubs (`.pyi` files) to reflect the deprecation
- Update all documentation, examples, and docs_app to use `signal()` and `computed()` exclusively
- If Phase 3a recommends deprecating `ReactiveList` / `ReactiveDict`: add `DeprecationWarning` to their constructors and document migration paths

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `reactive`: `signal()` SHALL be the primary signal creation API; `Signal()` constructor SHALL emit `DeprecationWarning`; `Reactive` alias SHALL be removed or deprecated; `computed()` SHALL be the sole Computed creation API
- `composables`: Escalate `signal()` composable's `Signal()` warning from `UserWarning` to `DeprecationWarning`; update deprecation message

## Impact

- `packages/webcompy/src/webcompy/signal/_signal.py` — `Signal.__init__` warning escalated to `DeprecationWarning`
- `packages/webcompy/src/webcompy/signal/__init__.py` — remove `Reactive` export if it's an alias; ensure `signal` and `computed` are the primary exports
- `packages/webcompy/src/webcompy/signal/_computed.py` — deprecate `Computed()` class constructor if separate from `computed()`
- All framework internal files using `Signal()` — migrate to `signal()` or `Signal._create()` as appropriate
- `docs_app/` — update all examples to use `signal()` and `computed()`
- Type stubs (`.pyi`) — mark `Signal.__init__` as deprecated
- If Phase 3a recommends: `packages/webcompy/src/webcompy/signal/_collection.py` — add `DeprecationWarning` to `ReactiveList()` / `ReactiveDict()`

## Known Issues Addressed

- "No element-level reactivity in ReactiveList/ReactiveDict" — if Phase 3a recommends deprecation, this issue is resolved by migrating to `Signal[list]` / `Signal[dict]`

## Non-goals

- Removing the `Signal` class entirely (it remains as the return type of `signal()` and for type annotations)
- Implementing ReactiveList/ReactiveDict deprecation migration (that would be Phase 3b, a separate implementation change)
- Module-level signal transfer (Phase 5)
- Changing the `computed()` API itself (it's already function-style)
