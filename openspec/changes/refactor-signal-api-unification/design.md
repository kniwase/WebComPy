## Context

Phase 2 introduced `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` as the recommended signal creation composables with `UserWarning` for `Signal()` direct construction. The framework's reactive vocabulary now has a mix of function-style and class-style APIs:

- `use_state(factory)` — function-style, transferable (Phase 2) ✓
- `Signal(value)` — class-style, deprecated via `UserWarning` (Phase 2)
- `computed(fn)` — function-style ✓ (to be renamed `use_computed()`)
- `Computed(fn)` — class-style (coexists with `computed()`)
- `use_reactive_list(factory)` — function-style, transferable (Phase 2) ✓
- `use_reactive_dict(factory)` — function-style, transferable (Phase 2) ✓
- `ReactiveList([...])` — class-style, retained (mutation ergonomics)
- `ReactiveDict({...})` — class-style, retained (mutation ergonomics)

This change completes the migration to a unified `use_*` composable API. The `Signal` and `Computed` classes remain as types (for annotations and as the runtime return type), but their constructors are deprecated with `DeprecationWarning`.

## Goals / Non-Goals

**Goals:**
- Escalate `Signal()` deprecation from `UserWarning` to `DeprecationWarning`
- Deprecate `Computed()` class constructor
- Rename `computed()` to `use_computed()` for naming consistency with `use_state()`
- Add `Computed._create()` classmethod as internal bypass
- Migrate all internal framework code to function-style APIs or `_create()` bypasses
- Update documentation, examples, type stubs, and specs

**Non-Goals:**
- Removing the `Signal` / `Computed` classes (they remain as types)
- Deprecating `ReactiveList` / `ReactiveDict` (retained per investigation)
- Changing `use_state()`, `use_reactive_list()`, `use_reactive_dict()` signatures

## Decisions

### Decision 1: Escalate to DeprecationWarning

**Choice**: Change `Signal.__init__` warning from `UserWarning` to `DeprecationWarning`.

**Rationale**: Phase 2 used `UserWarning` because the class was not yet being removed. This change establishes the intent to eventually remove the public constructor, making `DeprecationWarning` semantically correct. `DeprecationWarning` is visible by default in Python 3.12+ (PEP 565), ensuring users see it.

### Decision 2: Deprecate `Computed()` class constructor

**Choice**: Add `DeprecationWarning` to `Computed.__init__()`. `use_computed()` becomes the sole recommended way.

**Rationale**: Symmetry with `use_state()` / `Signal()`. The function-style API is cleaner and matches the unified `use_*` naming convention.

### Decision 3: Rename `computed()` to `use_computed()`

**Choice**: Rename the existing `computed()` function to `use_computed()`. Keep `computed` as a deprecated alias for backward compatibility.

**Rationale**: Naming consistency. All composables follow the `use_*` pattern: `use_state()`, `use_computed()`, `use_reactive_list()`, `use_reactive_dict()`, `use_async_result()`. The `computed()` name is the sole outlier.

### Decision 4: Add `Computed._create()` internal bypass

**Choice**: Add `Computed._create(fn)` classmethod that bypasses the deprecation warning, mirroring `Signal._create()`.

**Rationale**: Internal framework code creates `Computed` instances in several places (`_manager.py`, `_reactive_scoped_style.py`, `styles.py`, and inside `use_computed()` itself). These need a warning-free bypass.

### Decision 5: Internal migration strategy

**Choice**: Migrate framework internal code in two tiers:
1. **Transfer-required** (inside component setup): `Signal(value)` → `use_state(lambda: value)` where the signal needs SSR transfer
2. **Internal-only** (framework infrastructure, not in component setup): `Signal(value)` → `Signal._create(value)` (no transfer needed, no warnings)

Similarly for `Computed`:
1. **User-facing derivation**: `Computed(fn)` → `use_computed(fn)`
2. **Internal-only**: `Computed(fn)` → `Computed._create(fn)`

**Rationale**: Not all internal Signal usages need transfer. Using `use_state()` for non-transfer contexts would add unnecessary overhead (payload check, registration). `_create()` methods remain the internal bypass.

## Risks / Trade-offs

- **[Breaking change for `computed()` users]** Renaming `computed()` to `use_computed()` breaks code that imports it. → Mitigation: keep `computed` as a deprecated alias with `DeprecationWarning`; document the migration.

- **[Computed() deprecation impact]** If user code uses `Computed(fn)` directly, they'll see warnings. → Mitigation: `use_computed()` already exists (renamed from `computed()`); migration is mechanical.

- **[Spec staleness]** Existing `reactive/spec.md` and `signal-value-transfer/spec.md` scenarios use `Signal(value)` and `Computed(fn)` patterns. → Mitigation: add `openspec sync-specs` tasks to update all deprecated patterns in specs.

## Open Questions

- Should `computed` (the deprecated alias) be removed in this change or a future change? **Tentative answer: future change** — provide one release cycle of backward compatibility.
- Should `Computed._create()` also be available for external users? **Tentative answer: No** — it's an internal API marked with `_` prefix.
