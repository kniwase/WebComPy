## Why

Phase 2 (`feat-signal-composable`) introduced `use_state()` as the recommended signal creation API with `UserWarning` for `Signal()` direct construction. This change completes the API unification by escalating the deprecation level, deprecating `Computed()` class constructor, migrating `computed()` to `use_computed()`, and cleaning up internal usage.

This change depends on `feat-signal-composable` (Phase 2) — it escalates the `UserWarning` introduced there and builds on the `use_*` composable pattern.

## What Changes

- Escalate `Signal()` direct construction warning from `UserWarning` to `DeprecationWarning`
- Deprecate `Computed()` class constructor — add `DeprecationWarning` directing users to `use_computed()`
- Rename `computed()` function to `use_computed()` to align with the `use_*` composable naming convention
- Migrate all internal framework code from `Signal()` / `Signal._create()` to `use_state()` where transfer is needed, or keep `Signal._create()` for truly internal non-transfer contexts
- Migrate all internal `Computed()` constructor calls to `use_computed()` or `Computed._create()` for internal use
- Add `Computed._create()` classmethod as internal bypass (no warning)
- Update type stubs (`.pyi` files) to reflect the deprecation
- Update all documentation, examples, and docs_app to use `use_state()`, `use_computed()`, `use_reactive_list()`, `use_reactive_dict()` exclusively
- Run `openspec sync-specs` to update `reactive/spec.md` and `signal-value-transfer/spec.md` scenarios that use deprecated `Signal(value)` and `Computed(fn)` patterns

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `reactive`: `use_state()` SHALL be the primary signal creation API; `Signal()` constructor SHALL emit `DeprecationWarning`; `use_computed()` SHALL be the sole Computed creation API; `Computed()` constructor SHALL emit `DeprecationWarning`
- `composables`: Escalate `use_state()` composable's `Signal()` warning from `UserWarning` to `DeprecationWarning`; rename `computed()` to `use_computed()`; add `Computed()` deprecation

## Impact

- `packages/webcompy/src/webcompy/signal/_signal.py` — `Signal.__init__` warning escalated to `DeprecationWarning`
- `packages/webcompy/src/webcompy/signal/_computed.py` — `Computed.__init__` gains `DeprecationWarning`; add `Computed._create()` classmethod; rename `computed()` to `use_computed()`
- `packages/webcompy/src/webcompy/signal/__init__.py` — export `use_computed` instead of `computed`; keep `computed` as deprecated alias
- All framework internal files using `Signal()` / `Computed()` — migrate to `use_state()` / `use_computed()` or `Signal._create()` / `Computed._create()`
- `docs_app/` — update all examples to use `use_state()`, `use_computed()`, `use_reactive_list()`, `use_reactive_dict()`
- Type stubs (`.pyi`) — mark `Signal.__init__` and `Computed.__init__` as deprecated
- `openspec/specs/reactive/spec.md` — sync-specs to replace `Signal(value)` / `Computed(fn)` examples with `use_state()` / `use_computed()`
- `openspec/specs/signal-value-transfer/spec.md` — sync-specs to update Purpose section and any remaining class-style scenarios

## Known Issues Addressed

(none)

## Non-goals

- Removing the `Signal` or `Computed` class entirely (they remain as return types and type annotations)
- Deprecating `ReactiveList` / `ReactiveDict` (retained per investigation — mutation ergonomics justify keeping them)
- Module-level signal transfer (not pursued)
- Changing the `use_state()`, `use_reactive_list()`, `use_reactive_dict()` function signatures
