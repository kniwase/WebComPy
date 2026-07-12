## Why

Phase 2 (`feat-signal-composable`) introduced `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` as the primary signal creation composables. The `Signal`, `Computed`, `ReactiveList`, and `ReactiveDict` classes are internal APIs accessed through `webcompy.signal` — their constructors carry no warnings and are intended for framework internal use and type annotations.

The remaining inconsistency is `computed()`, the sole function-style API not following the `use_*` naming convention. Renaming it to `use_computed()` completes the API unification.

## What Changes

- Rename `computed()` to `use_computed()` in `webcompy.signal._computed`
- Export `use_computed` from `webcompy.signal` and add it to the top-level `webcompy` exports
- Remove `computed` from `webcompy.signal` exports (no deprecated alias)
- Update all internal imports, docs_app, CLI templates, and tests
- Update specs (`reactive/spec.md`, `composables/spec.md`, `signal-value-transfer/spec.md`) to use `use_computed()` instead of `computed()`
- Remove the `Computed as _Computed` import alias in `app/styles.py`; framework code SHALL use original class names without `_`-prefixed aliases
- Unify framework internal imports to use the public `webcompy.signal` path for exported names (replacing direct imports from `webcompy.signal._base`, `webcompy.signal._computed`, etc.)

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `reactive`: `use_computed()` replaces `computed()` as the Computed creation API
- `composables`: `computed()` renamed to `use_computed()`; removed from public API surface

## Impact

- `packages/webcompy/src/webcompy/signal/_computed.py` — rename `computed()` to `use_computed()`
- `packages/webcompy/src/webcompy/signal/__init__.py` — export `use_computed` instead of `computed`
- `packages/webcompy/src/webcompy/__init__.py` — add `use_computed` to top-level exports
- All framework internal files using `computed()` — migrate to `use_computed()`
- `docs_app/` — update all examples to use `use_computed()`
- `tests/` — update imports and usages
- `openspec/specs/reactive/spec.md` — sync-specs to replace `computed()` / `Computed()` scenarios with `use_computed()`
- `packages/webcompy/src/webcompy/app/styles.py` — remove `Computed as _Computed` alias; use `Computed` directly
- `packages/webcompy/src/webcompy/ports/_browser/_history.py` — unify import to `from webcompy.signal import SignalBase`
- `packages/webcompy/src/webcompy/router/_router.py` — unify import to `from webcompy.signal import computed_property`
- `packages/webcompy/src/webcompy/components/_reactive_scoped_style.py` — unify import to `from webcompy.signal import Computed`
- `packages/webcompy/src/webcompy/elements/types/_switch.py` — unify import to `from webcompy.signal import SignalBase`
- `packages/webcompy/src/webcompy/elements/types/_base.py` — unify import to `from webcompy.signal import SignalBase`
- `packages/webcompy/src/webcompy/elements/types/_text.py` — unify import to `from webcompy.signal import SignalBase`
- `packages/webcompy/src/webcompy/elements/typealias/_element_property.py` — unify import to `from webcompy.signal import SignalBase`
- `packages/webcompy/src/webcompy/hydration/_collect.py` — consolidate two private-module imports into one public import
- `packages/webcompy/src/webcompy/app/_app.py` — unify TYPE_CHECKING import to `from webcompy.signal import Computed`
- `packages/webcompy/src/webcompy/signal/_composable.py` — add `_resolve_factory()` shared helper for argument validation
- `packages/webcompy/src/webcompy/signal/_computed.py` — simplify `use_computed()` to single `Callable[[], T]` argument (remove key parameter, remove `@overload` and `_resolve_factory` usage, add `not callable` guard)
- `packages/webcompy/src/webcompy/ports/_history.py` — unify `SignalBase` import to `from webcompy.signal import SignalBase`
- `packages/webcompy/src/webcompy/elements/_head.py` — unify `Computed` import to `from webcompy.signal import Computed`
- `packages/webcompy/src/webcompy/elements/types/_element.py` — unify `SignalBase` import to `from webcompy.signal import SignalBase`
- `packages/webcompy/src/webcompy/components/_libs.py` — unify TYPE_CHECKING `SignalBase` import to `from webcompy.signal import SignalBase`
- `packages/webcompy/src/webcompy/components/_hooks.py` — split import: `SignalBase` to public path, `CallbackConsumerNode` stays on private path
- `packages/webcompy/src/webcompy/components/_context_manager.py` — split import: `EffectScope` to public path, `_active_scope` stays on private path
- `packages/webcompy/src/webcompy/app/styles.py` — fix docstring example in `reactive_block()` to use `Computed()` instead of `use_computed()`
- `packages/webcompy/src/webcompy/elements/types/_repeat.py` — `MultiLineTextElement` uses `Computed()` directly (infrastructure code, not component setup context)
- `openspec/specs/app-styles/spec.md` — scenario example uses `Computed()` to align with infrastructure code context (matching `styles.py` docstring)
- `openspec/specs/signal-value-transfer/spec.md` — remove stale change-name reference note
- `packages/webcompy/src/webcompy/signal/_composable.py` — fix `_resolve_factory()` first error message to include `func_name` for consistency; fix `_resolve_args()` `func_name` value to remove redundant `()` suffix
- `openspec/specs/composables/spec.md` — refine "no warning" scenario wording to clarify it refers to calling-context warning

## Known Issues Addressed

(none)

## Non-goals

- Adding runtime warnings to `Signal()` or `Computed()` constructors (these remain internal APIs accessible via `webcompy.signal`)
- Adding `Signal._create()` or `Computed._create()` classmethods (no warnings to bypass)
- Removing the `Signal` or `Computed` class (they remain as return types and type annotations)
- Deprecating `ReactiveList` / `ReactiveDict` (retained per investigation)
- Creating a deprecated `computed` alias (direct rename, no backward-compat shim)
