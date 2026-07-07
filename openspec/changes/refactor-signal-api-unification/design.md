## Context

Phase 2 introduced `signal()` as the recommended signal creation API with `UserWarning` for `Signal()` direct construction. The framework's reactive vocabulary now has a mix of function-style and class-style APIs:

- `signal(factory)` — function-style, transferable (Phase 2) ✓
- `Signal(value)` — class-style, deprecated via `UserWarning` (Phase 2)
- `computed(fn)` — function-style ✓
- `Computed(fn)` — class-style (may coexist with `computed()`)
- `Reactive` — possible alias for `Signal`
- `ReactiveList([...])` — class-style, under investigation (Phase 3a)
- `ReactiveDict({...})` — class-style, under investigation (Phase 3a)

This change completes the migration to a unified function-style API, matching Angular's `signal()` + `computed()` vocabulary. The `Signal` and `Computed` classes remain as types (for annotations and as the runtime return type), but their constructors are deprecated.

## Goals / Non-Goals

**Goals:**
- Escalate `Signal()` deprecation from `UserWarning` to `DeprecationWarning`
- Remove or deprecate the `Reactive` alias
- Deprecate `Computed()` class constructor (if separate from `computed()`)
- Migrate all internal framework code to function-style APIs
- Update documentation, examples, and type stubs
- Incorporate Phase 3a findings for ReactiveList/ReactiveDict if applicable

**Non-Goals:**
- Removing the `Signal` / `Computed` classes (they remain as types)
- Implementing ReactiveList/ReactiveDict removal (separate Phase 3b change)
- Changing the `signal()` or `computed()` function signatures
- Module-level transfer (Phase 5)

## Decisions

### Decision 1: Escalate to DeprecationWarning

**Choice**: Change `Signal.__init__` warning from `UserWarning` to `DeprecationWarning`.

**Rationale**: Phase 2 used `UserWarning` because the class was not yet being removed. Phase 4 establishes the intent to eventually remove the public constructor, making `DeprecationWarning` semantically correct. `DeprecationWarning` is visible by default in Python 3.12+ (PEP 565), ensuring users see it.

### Decision 2: Remove `Reactive` alias

**Choice**: If `Reactive` is an alias for `Signal`, remove it from the public API. Users should use `signal()` for creation and `Signal[T]` for type annotations.

**Rationale**: Having two names for the same concept (`Signal` and `Reactive`) creates confusion. `signal()` is the creation function; `Signal[T]` is the type. `Reactive` serves no purpose in the unified vocabulary.

**Migration**: `from webcompy.signal import Reactive` → `from webcompy.signal import Signal` (for type annotations); `Reactive(0)` → `signal(lambda: 0)` (for creation).

### Decision 3: Deprecate `Computed()` class constructor

**Choice**: If `Computed(fn)` exists as a separate class constructor (distinct from `computed(fn)`), add `DeprecationWarning` to it. `computed(fn)` becomes the sole recommended way.

**Rationale**: Symmetry with `signal()` / `Signal()`. The function-style API is cleaner and matches Angular's `computed()`.

### Decision 4: Internal migration strategy

**Choice**: Migrate framework internal code in two tiers:
1. **Transfer-required** (inside component setup): `Signal(value)` → `signal(lambda: value)` where the signal needs SSR transfer
2. **Internal-only** (framework infrastructure, not in component setup): `Signal(value)` → `Signal._create(value)` (no transfer needed, no warning)

**Rationale**: Not all internal Signal usages need transfer. Using `signal()` for non-transfer contexts would add unnecessary overhead (payload check, registration). `Signal._create()` remains the internal bypass.

## Risks / Trade-offs

- **[Breaking change for `Reactive` users]** Removing the `Reactive` alias breaks code that imports it. → Mitigation: provide a deprecation period (emit warning in this change, remove in a later change); document the migration.

- **[Computed() deprecation impact]** If user code uses `Computed(fn)` directly, they'll see warnings. → Mitigation: `computed(fn)` already exists and is the recommended path; migration is mechanical.

- **[Phase 3a dependency]** If Phase 3a has not completed, this change cannot incorporate ReactiveList/ReactiveDict deprecation findings. → Mitigation: Phase 4 proceeds with Signal/Computed unification regardless; ReactiveList/ReactiveDict changes can be a follow-up.

## Open Questions

- Should `Signal._create()` also be deprecated for external users (non-framework code)? **Tentative answer: No** — it's an internal API marked with `_` prefix; external users shouldn't use it. But we can't prevent imports.
- Should the `Reactive` removal happen in this change or a separate change? **Tentative answer: This change** — it's part of the unification scope.
