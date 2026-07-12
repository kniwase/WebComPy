## Context

Phase 2 introduced `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` as the recommended signal creation composables. The `Signal`, `Computed`, `ReactiveList`, and `ReactiveDict` classes remain accessible via `webcompy.signal` for type annotations and internal use — their constructors carry no runtime warnings.

The framework's reactive vocabulary is now:

- `use_state(factory)` — function-style, transferable ✓
- `Signal(value)` — class-style, internal (no warning) ✓
- `use_computed(fn)` — function-style (to be renamed from `computed()`) ✓
- `Computed(fn)` — class-style, internal (no warning) ✓
- `use_reactive_list(factory)` — function-style, transferable ✓
- `use_reactive_dict(factory)` — function-style, transferable ✓

The sole outlier is `computed()`, which does not follow the `use_*` naming convention. Renaming it to `use_computed()` completes the unification.

## Goals / Non-Goals

**Goals:**
- Rename `computed()` to `use_computed()` for naming consistency with `use_state()` etc.
- Export `use_computed` from `webcompy` top-level (alongside `use_state`, `use_reactive_list`, `use_reactive_dict`)
- Remove `computed` from `webcompy.signal` exports (no deprecated alias)
- Update all internal usage, docs_app, templates, tests, and specs

**Non-Goals:**
- Adding runtime warnings to `Signal()` or `Computed()` constructors
- Adding `_create()` bypass methods (unnecessary without warnings)
- Removing `Signal` / `Computed` classes from `webcompy.signal` (they remain for type annotations)
- Deprecating `ReactiveList` / `ReactiveDict`
- Changing `use_state()`, `use_reactive_list()`, `use_reactive_dict()` signatures

## Decisions

### Decision 1: Rename `computed()` to `use_computed()`

**Choice**: Rename the `computed()` function in `_computed.py` to `use_computed()`. Export it from `webcompy.signal` and add to top-level `webcompy` exports. No deprecated alias.

**Rationale**: Naming consistency. All composables follow the `use_*` pattern: `use_state()`, `use_computed()`, `use_reactive_list()`, `use_reactive_dict()`, `use_async_result()`. The `computed()` name is the sole outlier. Creating a deprecated alias adds maintenance burden with no benefit — `computed()` is a minor API surface and the migration is a simple find-and-replace.

### Decision 2: No DeprecationWarning on Signal/Computed constructors

**Choice**: Do not add warnings. `Signal` and `Computed` remain internal classes (in underscore-prefixed modules `_base.py`, `_computed.py`) accessible via `webcompy.signal`. Their constructors are used by the `use_*` composables internally and by any third-party code that needs to create instances for framework extension.

**Rationale**: Python's module-level privacy convention (`_module.py`) is the natural boundary. Adding runtime warnings to classes used internally by the framework creates self-inflicted noise that requires bypass mechanisms (`_create()`). The `use_*` composables ARE the public creation API — this is communicated through exports and documentation, not runtime penalties.

### Decision 3: No internal code migration

**Choice**: Framework internal code that uses `Signal(value)` or `Computed(fn)` directly keeps those constructor calls as-is. No `_create()` bypass is introduced.

**Rationale**: Without runtime warnings, internal code can use the most natural API. The `use_*` composables are for user-facing code (component setup) where SSR transfer matters. Framework infrastructure code (signal manager, style system, async results) accesses `Signal`/`Computed` directly, which is fine.

### Decision 4: Import path convention for signal classes

**Choice**: Framework code SHALL import publicly-exported signal names from `webcompy.signal` — the public package surface — not from private submodules (`webcompy.signal._base`, `webcompy.signal._computed`, etc.). `_`-prefixed aliases (e.g., `Computed as _Computed`) SHALL NOT be used. Non-exported internal symbols (`consumer_destroy`, `CallbackConsumerNode`, `producer_accessed`, etc.) MAY be imported from private submodules, as they are not available via `webcompy.signal`.

**Rationale**: `webcompy.signal.__all__` is the canonical public surface. Using it consistently avoids confusion about which import path to use and eliminates unnecessary aliases that suggest a distinction that doesn't exist (both names refer to the same class). The `_`-prefix convention is reserved for indicating non-public symbols — using it on an alias of an already-public class is misleading.

## Usage Guidance: Composable vs Direct Constructor

```
                    Signal / Computed creation
                    ═══════════════════════════

    ┌───────────────────────┴───────────────────────┐
    │                                               │
    ▼                                               ▼
  use_state(factory)                          Signal(value)
  use_computed(fn)                            Computed(fn)
  use_reactive_list(factory)                  ReactiveList([...])
  use_reactive_dict(factory)                  ReactiveDict({...})
    │                                               │
    ├─ SSR transfer enabled                      ├─ No warnings
    ├─ Automatic key management                    ├─ No transfer
    └─ Public API (under webcompy)                 └─ Via webcompy.signal
```

### When to use `use_*` composables

- **Component setup functions** — Create state inside the component setup. SSR transfer is enabled.
- **User-facing application code** — Can be imported directly from `webcompy`. This is the API users should touch first.

```python
from webcompy import use_state, use_computed

@define_component
def Counter():
    count = use_state(lambda: 0)          # ← composable
    doubled = use_computed(lambda: count.value * 2)  # ← composable
    ...
```

### When to use `Signal()` / `Computed()` directly

- **Module-level (global) state** — State whose lifetime spans the entire application, existing outside any component.

```python
from webcompy.signal import Signal

_global_counter = Signal(0)  # module-level, no component context

class CounterStore:
    def __init__(self):
        self._count = Signal(0)
```

- **Plugins** — Internal state for `WebComPyPlugin`. Plugin setup is independent of component setup, so it is outside the `use_state()` context.

- **DI providers** — Holds values injected via `provide()`. DI scopes are constructed outside component setup.

- **Third-party extensions** — Libraries that depend on the framework's internal API. The `Signal` / `Computed` classes are public internal types and can be used without warnings.

- **Framework infrastructure** — The framework's own internal implementation, such as the signal manager (`_manager.py`), scoped style system (`_reactive_scoped_style.py`), and `AsyncResult` internals.

### Design principle

The `use_*` composables are the public API for creating user-facing state that requires transfer, while `Signal()` / `Computed()` are the internal API for creating internal/infrastructure state that does not require transfer.

The two are not in opposition; they are natural choices depending on context. Rather than prohibiting one side with runtime warnings, we guide the choice through the export surface (`webcompy` vs `webcompy.signal`) and documentation.

## Risks / Trade-offs

- **[Breaking change for `computed()` users]** Renaming without an alias breaks all existing `computed()` usage. → Mitigation: `computed()` is currently only exported from `webcompy.signal`, not from the top-level `webcompy`, so its user-facing surface is small. Mechanical find-and-replace covers all cases.

- **[Spec staleness]** Existing `reactive/spec.md` scenarios use `Signal(value)` and `Computed(fn)` patterns. → Mitigation: sync-specs to update scenarios to use `use_state()` and `use_computed()` where user-facing, keeping constructor access for internal contexts.

## Open Questions

(none)

## Not In Scope

- **`computed_property` decorator**: This decorator is part of the class-based component API and is retained as-is. Like the `Computed` class (which remains as a type), `computed_property` continues to work without changes. A future change may address class-based API consistency holistically.
