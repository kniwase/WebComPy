## Why

WebComPy's reactive system was redesigned in the `refactor-reactive-signals` change to adopt Angular Signals' push/pull architecture — per-node graph state, version tracking, lazy computed evaluation, and `consumer_destroy()` cleanup. The internal implementation now mirrors Angular Signals precisely, but the public API still uses the "Reactive" naming inherited from the early prototype. This naming divergence causes confusion: the architecture is Signals-based, but the primitives are called `Reactive`, `ReactiveBase`, and `ReactiveList`. Renaming to align with industry conventions (Angular `signal()`, Preact `signal()`, TC39 `Signal.State`) makes the framework immediately understandable to developers familiar with modern frontend patterns and improves discoverability — "Python Signals framework" is a more accurate and searchable description than "Python Reactive framework" (which conflates with RxPY/ReactiveX).

## What Changes

- **BREAKING**: Rename `Reactive` → `Signal` (the core writable reactive primitive)
- **BREAKING**: Rename `ReactiveBase` → `SignalBase` (abstract base class for all signal nodes)
- **BREAKING**: Rename `ReadonlyReactive` → `ReadonlySignal` (read-only signal wrapper)
- **BREAKING**: Rename `webcompy.reactive` module → `webcompy.signal` (the package directory and all imports)
- **BREAKING**: Rename internal graph classes `ReactiveNode` → `SignalNode`, `ReactiveEdge` → `SignalEdge`
- **BREAKING**: Rename `ReactiveReceivable` → `SignalReceivable`, `__reactive_members__` → `__signal_members__`, `__purge_reactive_members__` → `__purge_signal_members__`, `__set_reactive_member__` → `__set_signal_member__`
- Keep `ReactiveList` and `ReactiveDict` unchanged — they are collection-specific types where "Reactive" describes the behavior (a reactive wrapper around list/dict) and "SignalList"/"SignalDict" would be ambiguous (could mean "a list of signals")
- Keep `Computed`, `computed`, `computed_property`, `effect`, `EffectHandle`, `EffectScope`, `readonly` unchanged — these already match Signal conventions
- Keep `_change_event` and `_get_event` decorator names unchanged (internal implementation detail)
- Update all type aliases (`AttrValue`, `ElementChildren`, `ChildNode`) that reference `ReactiveBase` → `SignalBase`
- Update all `isinstance(..., ReactiveBase)` checks → `isinstance(..., SignalBase)`
- Update all `from webcompy.reactive import ...` → `from webcompy.signal import ...`
- Update module re-export in `webcompy/__init__.py`
- Update openspec specs to use "Signal" terminology
- Update tests and e2e app code

## Known Issues Addressed

- Multiple global singletons (ReactiveStore) — already removed in previous change; this renaming further clarifies the architecture by removing "Reactive" naming that implied a singleton store pattern

## Non-goals

- Changing `ReactiveList` → `SignalList` or `ReactiveDict` → `SignalDict` — the "Signal" prefix is misleading for collection wrappers
- Changing `Computed` → `ComputedSignal` or similar — `Computed` already aligns with Angular/Preact conventions
- Adding new public API surface — this is purely a rename, no behavioral changes
- Providing a backward-compatibility import shim (`from webcompy.reactive import ...` → `from webcompy.signal import ...`) — WebComPy is pre-stable; clean break is preferred
- Changing any behavior, semantics, or performance — only names change

## Capabilities

### New Capabilities

None — this is a pure rename with no new capabilities.

### Modified Capabilities

- `reactive`: Rename all public primitives from "Reactive" to "Signal" terminology. The spec-level requirements do not change (equality checks, lazy evaluation, dynamic dependencies, deterministic cleanup all remain), but the names of primitives change: `Reactive` → `Signal`, `ReactiveBase` → `SignalBase`, `ReadonlyReactive` → `ReadonlySignal`. The module path changes from `webcompy.reactive` to `webcompy.signal`.
- `architecture`: Update the architectural description of the reactive system to use "Signal" terminology. No requirement changes — only terminology.
- `composables`: Update type references from `Reactive` → `Signal`. No requirement changes.
- `elements`: Update type aliases (`AttrValue`, `ElementChildren`) that reference `ReactiveBase` → `SignalBase`. No requirement changes.

## Impact

- **Core reactive module** (`webcompy/reactive/` → `webcompy/signal/`): Directory rename, all files renamed or their contents updated. `Reactive` → `Signal`, `ReactiveBase` → `SignalBase`, `ReactiveNode` → `SignalNode`, `ReactiveEdge` → `SignalEdge`, `ReactiveReceivable` → `SignalReceivable`, `ReadonlyReactive` → `ReadonlySignal`. `ReactiveList` and `ReactiveDict` remain in `webcompy/signal/` with unchanged names.
- **Element system** (`webcompy/elements/`): All imports, type annotations, and `isinstance` checks updated. `AttrValue`, `ElementChildren` type aliases updated to use `SignalBase`.
- **Component system** (`webcompy/components/`): Import path changes, type annotation changes.
- **Router** (`webcompy/router/`): Import path changes, type annotation changes.
- **Async** (`webcompy/aio/`): Import path changes, type annotation changes.
- **App** (`webcompy/app/`): Import path changes.
- **Public API**: **BREAKING** — all `from webcompy.reactive import Reactive` → `from webcompy.signal import Signal`. No backward-compatibility shim.
- **Tests and e2e**: All import paths and type references updated.
- **OpenSpec specs**: Terminology updated throughout.