## Context

WebComPy's reactive system was redesigned in `refactor-reactive-signals` to adopt Angular Signals' push/pull architecture. The internal implementation — `ReactiveNode`, `ReactiveEdge`, version tracking, `consumer_destroy()`, lazy computed evaluation, effect scoping — is now a faithful Signals implementation. However, the public API still uses "Reactive" terminology inherited from the pre-signals architecture: `Reactive`, `ReactiveBase`, `ReactiveList`, `ReactiveDict`, `ReadonlyReactive`, the `webcompy.reactive` module path, and internal names like `ReactiveReceivable`, `ReactiveNode`, `ReactiveEdge`, `__reactive_members__`.

This naming mismatch is confusing: the architecture IS Signals, but the names say Reactive. The current names also conflict with the broader frontend ecosystem where "Reactive" connotes ReactiveX/Rx-style stream programming (observables, operators, schedulers) rather than fine-grained state primitives.

The mapping is straightforward:

| Current | Proposed | Rationale |
|---------|----------|-----------|
| `Reactive` | `Signal` | Matches Angular `signal()`, Preact `signal()`, TC39 `Signal.State` |
| `ReactiveBase` | `SignalBase` | Base class for all signal nodes |
| `ReadonlyReactive` | `ReadonlySignal` | Read-only signal wrapper |
| `ReactiveList` | `ReactiveList` | **Kept** — "reactive list" is unambiguous; "signal list" is ambiguous (a list of signals?) |
| `ReactiveDict` | `ReactiveDict` | **Kept** — same reasoning |
| `ReactiveNode` | `SignalNode` | Internal graph node |
| `ReactiveEdge` | `SignalEdge` | Internal graph edge |
| `ReactiveReceivable` | `SignalReceivable` | Mixin for objects that hold signal members |
| `webcompy.reactive` | `webcompy.signal` | Module path |
| `__reactive_members__` | `__signal_members__` | Dunder attribute |
| `__set_reactive_member__` | `__set_signal_member__` | Dunder method |
| `__purge_reactive_members__` | `__purge_signal_members__` | Dunder method |
| `_reactive_activated` | `_signal_activated` | Private attribute |

`Computed`, `computed`, `computed_property`, `effect`, `EffectHandle`, `EffectScope`, `readonly` — these already match Signal-era conventions and remain unchanged.

## Goals / Non-Goals

**Goals:**

- Rename all "Reactive"-prefixed public API primitives to "Signal"-prefixed equivalents
- Rename the `webcompy.reactive` module to `webcompy.signal`
- Rename all internal "Reactive"-prefixed classes and attributes
- Update all imports, type annotations, `isinstance` checks, and documentation across the entire codebase
- Update openspec specs to use "Signal" terminology

**Non-Goals:**

- Behavioral changes of any kind — this is purely a rename
- Adding backward-compatibility imports or deprecation warnings in `webcompy.reactive` — WebComPy is pre-stable
- Renaming `ReactiveList`/`ReactiveDict` — "SignalList"/"SignalDict" is ambiguous
- Renaming `Computed`, `computed`, `computed_property`, `effect`, `readonly` — they already follow Signal conventions
- Adding new public API surface
- Changing the `_change_event`/`_get_event` decorator names (internal implementation detail)

## Decisions

### Decision 1: Keep `ReactiveList` and `ReactiveDict` unchanged

**Choice:** `ReactiveList` and `ReactiveDict` keep their current names and move to the `webcompy.signal` module.

**Alternatives considered:**

- **Rename to `SignalList`/`SignalDict`:** Ambiguous — could mean "a Signal whose value is a list" (correct) or "a list of Signal instances" (wrong). The `Signal` prefix works for scalar primitives but not for collection wrappers.
- **Rename to `ReactiveList`/`ReactiveDict` in `webcompy.signal`:** This is the chosen approach. `ReactiveList` reads as "a reactive (wrapper around a) list" which is accurate and unambiguous.

**Rationale:** The `Reactive` prefix for collection types describes a behavior pattern ("reactive wrapper around list/dict"), not the Signal primitive. This is analogous to how Angular has no `SignalList` equivalent — it uses `signal()` with a plain array. WebComPy's `ReactiveList`/`ReactiveDict` are more akin to Vue's `reactive()` for collections (which Vue keeps as `reactive` distinct from `ref`). Keeping the names avoids ambiguity.

### Decision 2: Module rename strategy — clean break

**Choice:** Rename `webcompy/reactive/` directory to `webcompy/signal/` and update all imports in a single commit. No backward-compatibility re-export module.

**Alternatives considered:**

- **Keep `webcompy/reactive/` as re-export shim:** Add `webcompy/reactive/__init__.py` that re-exports everything from `webcompy/signal/` with a deprecation warning. Increases maintenance burden and delays the clean break.
- **Use Python namespace package for dual paths:** Overly complex for a pre-stable library.

**Rationale:** WebComPy has no published stable version. Breaking changes are expected and acceptable. A clean break is simpler, less code to maintain, and makes the transition complete in one step.

### Decision 3: File naming within `webcompy/signal/`

**Choice:** Rename the module files to match the new naming:

| Current | Proposed |
|---------|----------|
| `webcompy/reactive/_base.py` | `webcompy/signal/_base.py` |
| `webcompy/reactive/_graph.py` | `webcompy/signal/_graph.py` |
| `webcompy/reactive/_computed.py` | `webcompy/signal/_computed.py` |
| `webcompy/reactive/_list.py` | `webcompy/signal/_list.py` |
| `webcompy/reactive/_dict.py` | `webcompy/signal/_dict.py` |
| `webcompy/reactive/_readonly.py` | `webcompy/signal/_readonly.py` |
| `webcompy/reactive/_effect.py` | `webcompy/signal/_effect.py` |
| `webcompy/reactive/_composable.py` | `webcompy/signal/_composable.py` |
| `webcompy/reactive/_container.py` | `webcompy/signal/_container.py` |
| `webcompy/reactive/__init__.py` | `webcompy/signal/__init__.py` |

File names themselves (e.g., `_base.py`, `_graph.py`) do not contain "Reactive" so they don't need content changes beyond imports.

### Decision 4: Type alias updates

**Choice:** Update type aliases that reference `ReactiveBase`:

| Current | Proposed |
|---------|----------|
| `AttrValue = ReactiveBase[Any] \| str \| int \| bool` | `AttrValue = SignalBase[Any] \| str \| int \| bool` |
| `ElementChildren = ElementAbstract \| ReactiveBase[Any] \| str \| None` | `ElementChildren = ElementAbstract \| SignalBase[Any] \| str \| None` |
| `ChildNode = ElementBase \| TextElement \| ... \| ReactiveBase[Any] \| str \| None` | `ChildNode = ElementBase \| TextElement \| ... \| SignalBase[Any] \| str \| None` |
| `SwitchCasesReactive` | `SwitchCasesSignal` |
| `SwitchCasesReactiveList` | `SwitchCasesSignalList` |

Internal type aliases (`SwitchCasesReactive` → `SwitchCasesSignal`) change because they describe signal-based switching conditions, not "reactive" in the collection-wrapper sense.

### Decision 5: Dunder attribute naming

**Choice:** Rename dunder attributes consistently:

| Current | Proposed |
|---------|----------|
| `__reactive_members__` | `__signal_members__` |
| `__set_reactive_member__` | `__set_signal_member__` |
| `__purge_reactive_members__` | `__purge_signal_members__` |

These are name-mangled Python dunder attributes used internally by the `SignalReceivable` mixin. They are not part of the public API, but renaming them maintains consistency and avoids confusion about whether "reactive members" are `Signal` instances.

## Risks / Trade-offs

**[Risk: Large diff with no behavioral change]** → Mitigation: Use automated find-and-replace (sed/ripgrep) with manual review of edge cases. The entire change should be reviewable as a pure rename with no logic changes.

**[Risk: Missing import path updates causing runtime errors]** → Mitigation: Comprehensive grep for `webcompy.reactive`, `ReactiveBase`, `Reactive(`, `isinstance.*ReactiveBase` across the entire codebase. Run full test suite (unit + e2e) to catch any missed references.

**[Risk: `signal` module name conflicts with Python stdlib `signal`]** → Mitigation: The stdlib `signal` module is for OS signal handling and is imported as `import signal`, never as `from signal import Signal`. WebComPy users import as `from webcompy.signal import Signal`. No practical conflict exists. Additionally, `webcompy.signal` is a package (directory), while stdlib `signal` is a module (file), so even `import webcompy.signal` is unambiguous.

**[Risk: ReactiveList/ReactiveDict naming inconsistency]** → Accept the inconsistency. The names are clear in context: `ReactiveList` is "a reactive list wrapper", `Signal` is "a reactive value cell". This mirrors Vue's pattern where `ref()` (scalar) and `reactive()` (collection) coexist.

## Open Questions

- Should `_change_event` and `_get_event` decorator names change to `_signal_change`/`_signal_get` or remain as-is? They are internal implementation details, not part of the public API. Recommendation: keep as-is for now — they describe event semantics, not naming conventions.