## 1. Module Directory Rename

- [x] 1.1 Rename `webcompy/reactive/` directory to `webcompy/signal/` and update `webcompy/__init__.py` to export `signal` instead of `reactive`
- [x] 1.2 Update all `from webcompy.reactive import ...` statements across the entire codebase to `from webcompy.signal import ...` (use grep/ruff to find all occurrences)
- [x] 1.3 Update all `from webcompy.reactive._xxx import ...` internal imports to `from webcompy.signal._xxx import ...`

## 2. Core Class Renames

- [x] 2.1 Rename `Reactive` class to `Signal` in `webcompy/signal/_base.py` and update `__all__` in `webcompy/signal/__init__.py`
- [x] 2.2 Rename `ReactiveBase` class to `SignalBase` in `webcompy/signal/_base.py` and update `__all__`
- [x] 2.3 Rename `ReadonlyReactive` class to `ReadonlySignal` in `webcompy/signal/_readonly.py` and update imports
- [x] 2.4 Rename `ReactiveNode` class to `SignalNode` in `webcompy/signal/_graph.py` and update all references within `_graph.py`
- [x] 2.5 Rename `ReactiveEdge` class to `SignalEdge` in `webcompy/signal/_graph.py` and update all references within `_graph.py`
- [x] 2.6 Rename `ReactiveReceivable` class to `SignalReceivable` in `webcompy/signal/_container.py` and update all references

## 3. Dunder and Attribute Renames

- [x] 3.1 Rename `__reactive_members__` to `__signal_members__` in `webcompy/signal/_container.py` and all references
- [x] 3.2 Rename `__set_reactive_member__` to `__set_signal_member__` in `webcompy/signal/_container.py` and all references
- [x] 3.3 Rename `__purge_reactive_members__` to `__purge_signal_members__` in `webcompy/signal/_container.py` and all references
- [x] 3.4 Rename `_reactive_activated` to `_signal_activated` in `webcompy/elements/types/_switch.py` and `webcompy/elements/types/_repeat.py` and all references

## 4. Type Alias and Reference Updates

- [x] 4.1 Update `AttrValue` type alias in `webcompy/elements/typealias/_element_property.py` from `ReactiveBase[Any]` to `SignalBase[Any]`
- [x] 4.2 Update `ElementChildren` type alias in same file from `ReactiveBase[Any]` to `SignalBase[Any]`
- [x] 4.3 Update `ChildNode` type alias in `webcompy/elements/generators.py` from `ReactiveBase[Any]` to `SignalBase[Any]`
- [x] 4.4 Rename `SwitchCasesReactive` to `SwitchCasesSignal` and `SwitchCasesReactiveList` to `SwitchCasesSignalList` in `webcompy/elements/types/_switch.py`
- [x] 4.5 Update all `isinstance(..., ReactiveBase)` checks across the codebase to `isinstance(..., SignalBase)`

## 5. Cross-Module Import and Reference Updates

- [x] 5.1 Update all imports in `webcompy/elements/` (types, generators, typedef) from `webcompy.reactive` to `webcompy.signal` and from `ReactiveBase` to `SignalBase`
- [x] 5.2 Update all imports in `webcompy/components/` from `webcompy.reactive` to `webcompy.signal` and update `ReactiveBase`/`Reactive` references to `SignalBase`/`Signal`
- [x] 5.3 Update all imports in `webcompy/router/` from `webcompy.reactive` to `webcompy.signal` and update class references
- [x] 5.4 Update all imports in `webcompy/aio/` from `webcompy.reactive` to `webcompy.signal` and update class references
- [x] 5.5 Update all imports in `webcompy/app/` from `webcompy.reactive` to `webcompy.signal` and update class references
- [x] 5.6 Update all imports in `webcompy/ajax/` if they reference `webcompy.reactive`
- [x] 5.7 Update `HeadReactive` TypedDict in `webcompy/app/_root_component.py` — renamed to `HeadSignal`

## 6. Test Updates

- [x] 6.1 Update `tests/test_reactive.py` — renamed to `tests/test_signal.py`, updated all imports from `webcompy.reactive` to `webcompy.signal`, updated `Reactive` → `Signal`, `ReactiveBase` → `SignalBase` references
- [x] 6.2 Update `tests/test_effect.py` — updated all imports from `webcompy.reactive` to `webcompy.signal`
- [x] 6.3 Update `tests/test_graph.py` — updated all imports from `webcompy.reactive._graph` to `webcompy.signal._graph`, updated `ReactiveNode` → `SignalNode`, `ReactiveEdge` → `SignalEdge`
- [x] 6.4 Update `tests/test_list_mutation.py`, `tests/test_switch.py`, `tests/test_repeat.py`, `tests/test_keyed_repeat.py`, `tests/test_nested_dynamic.py`, `tests/test_elements.py`, `tests/test_components.py`, `tests/test_hooks.py`, `tests/test_async_result.py` — updated all imports and class references
- [x] 6.5 Update `tests/e2e/` test files and e2e app code — updated all imports and class references, renamed `reactive.py` → `signal.py`

## 7. Documentation and Spec Updates

- [x] 7.1 Update `openspec/specs/reactive/spec.md` — replaced "Reactive" terminology with "Signal" terminology throughout (class names, module path references, requirement titles)
- [x] 7.2 Update `openspec/specs/architecture/spec.md` — replaced signal system references
- [x] 7.3 Update `openspec/specs/composables/spec.md` — replaced `Signal` references where `Reactive` was used
- [x] 7.4 Update `openspec/specs/nested-dynamic-element/spec.md` — replaced reactive callback references with signal subscription references
- [x] 7.5 Update `openspec/specs/elements/spec.md` — replaced `Reactive` references with `Signal`
- [x] 7.6 Update `openspec/specs/overview/spec.md` — replaced `Reactive` terminology
- [x] 7.7 Update `openspec/config.yaml` — replaced `ReactiveStore` singleton reference, `ReactiveReceivable` → `SignalReceivable`, `__purge_reactive_members__` → `__purge_signal_members__`

## 8. Verification

- [x] 8.1 Run `uv run ruff check .` and fix any lint errors
- [x] 8.2 Run `uv run pyright` and fix any type errors
- [x] 8.3 Run `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e` and ensure all 330+ tests pass
- [x] 8.4 Grep for any remaining `webcompy.reactive`, `ReactiveBase`, `Reactive(` (as class instantiation, not `ReactiveList`/`ReactiveDict`), `ReactiveNode`, `ReactiveEdge`, `ReactiveReceivable`, `ReadonlyReactive`, `__reactive_members__` references that should have been renamed