## 1. Module Directory Rename

- [ ] 1.1 Rename `webcompy/reactive/` directory to `webcompy/signal/` and update `webcompy/__init__.py` to export `signal` instead of `reactive`
- [ ] 1.2 Update all `from webcompy.reactive import ...` statements across the entire codebase to `from webcompy.signal import ...` (use grep/ruff to find all occurrences)
- [ ] 1.3 Update all `from webcompy.reactive._xxx import ...` internal imports to `from webcompy.signal._xxx import ...`

## 2. Core Class Renames

- [ ] 2.1 Rename `Reactive` class to `Signal` in `webcompy/signal/_base.py` and update `__all__` in `webcompy/signal/__init__.py`
- [ ] 2.2 Rename `ReactiveBase` class to `SignalBase` in `webcompy/signal/_base.py` and update `__all__`
- [ ] 2.3 Rename `ReadonlyReactive` class to `ReadonlySignal` in `webcompy/signal/_readonly.py` and update imports
- [ ] 2.4 Rename `ReactiveNode` class to `SignalNode` in `webcompy/signal/_graph.py` and update all references within `_graph.py`
- [ ] 2.5 Rename `ReactiveEdge` class to `SignalEdge` in `webcompy/signal/_graph.py` and update all references within `_graph.py`
- [ ] 2.6 Rename `ReactiveReceivable` class to `SignalReceivable` in `webcompy/signal/_container.py` and update all references

## 3. Dunder and Attribute Renames

- [ ] 3.1 Rename `__reactive_members__` to `__signal_members__` in `webcompy/signal/_container.py` and all references
- [ ] 3.2 Rename `__set_reactive_member__` to `__set_signal_member__` in `webcompy/signal/_container.py` and all references
- [ ] 3.3 Rename `__purge_reactive_members__` to `__purge_signal_members__` in `webcompy/signal/_container.py` and all references
- [ ] 3.4 Rename `_reactive_activated` to `_signal_activated` in `webcompy/elements/types/_switch.py` and `webcompy/elements/types/_repeat.py` and all references

## 4. Type Alias and Reference Updates

- [ ] 4.1 Update `AttrValue` type alias in `webcompy/elements/typealias/_element_property.py` from `ReactiveBase[Any]` to `SignalBase[Any]`
- [ ] 4.2 Update `ElementChildren` type alias in same file from `ReactiveBase[Any]` to `SignalBase[Any]`
- [ ] 4.3 Update `ChildNode` type alias in `webcompy/elements/generators.py` from `ReactiveBase[Any]` to `SignalBase[Any]`
- [ ] 4.4 Rename `SwitchCasesReactive` to `SwitchCasesSignal` and `SwitchCasesReactiveList` to `SwitchCasesSignalList` in `webcompy/elements/types/_switch.py`
- [ ] 4.5 Update all `isinstance(..., ReactiveBase)` checks across the codebase to `isinstance(..., SignalBase)`

## 5. Cross-Module Import and Reference Updates

- [ ] 5.1 Update all imports in `webcompy/elements/` (types, generators, typedef) from `webcompy.reactive` to `webcompy.signal` and from `ReactiveBase` to `SignalBase`
- [ ] 5.2 Update all imports in `webcompy/components/` from `webcompy.reactive` to `webcompy.signal` and update `ReactiveBase`/`Reactive` references to `SignalBase`/`Signal`
- [ ] 5.3 Update all imports in `webcompy/router/` from `webcompy.reactive` to `webcompy.signal` and update class references
- [ ] 5.4 Update all imports in `webcompy/aio/` from `webcompy.reactive` to `webcompy.signal` and update class references
- [ ] 5.5 Update all imports in `webcompy/app/` from `webcompy.reactive` to `webcompy.signal` and update class references
- [ ] 5.6 Update all imports in `webcompy/ajax/` if they reference `webcompy.reactive`
- [ ] 5.7 Update `HeadReactive` TypedDict in `webcompy/app/_root_component.py` (review whether to rename to `HeadSignal` or keep as-is)

## 6. Test Updates

- [ ] 6.1 Update `tests/test_reactive.py` — rename to `tests/test_signal.py`, update all imports from `webcompy.reactive` to `webcompy.signal`, update `Reactive` → `Signal`, `ReactiveBase` → `SignalBase` references
- [ ] 6.2 Update `tests/test_effect.py` — update all imports from `webcompy.reactive` to `webcompy.signal`
- [ ] 6.3 Update `tests/test_graph.py` — update all imports from `webcompy.reactive._graph` to `webcompy.signal._graph`, update `ReactiveNode` → `SignalNode`, `ReactiveEdge` → `SignalEdge`
- [ ] 6.4 Update `tests/test_list_mutation.py`, `tests/test_switch.py`, `tests/test_repeat.py`, `tests/test_keyed_repeat.py`, `tests/test_nested_dynamic.py`, `tests/test_elements.py`, `tests/test_components.py`, `tests/test_hooks.py`, `tests/test_async_result.py` — update all imports and class references
- [ ] 6.5 Update `tests/e2e/` test files and e2e app code — update all imports and class references

## 7. Documentation and Spec Updates

- [ ] 7.1 Update `openspec/specs/reactive/spec.md` — replace "Reactive" terminology with "Signal" terminology throughout (class names, module path references, requirement titles)
- [ ] 7.2 Update `openspec/specs/architecture/spec.md` — replace signal system references
- [ ] 7.3 Update `openspec/specs/composables/spec.md` — replace `Signal` references where `Reactive` was used
- [ ] 7.4 Update `openspec/specs/nested-dynamic-element/spec.md` — replace reactive callback references with signal subscription references
- [ ] 7.5 Update `openspec/specs/elements/spec.md` if it references `ReactiveBase` or `Reactive`
- [ ] 7.6 Update `openspec/specs/overview/spec.md` if it references `Reactive` terminology
- [ ] 7.7 Update `openspec/config.yaml` if it references `webcompy.reactive`

## 8. Verification

- [ ] 8.1 Run `uv run ruff check .` and fix any lint errors
- [ ] 8.2 Run `uv run pyright` and fix any type errors
- [ ] 8.3 Run `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e` and ensure all 330+ tests pass
- [ ] 8.4 Grep for any remaining `webcompy.reactive`, `ReactiveBase`, `Reactive(` (as class instantiation, not `ReactiveList`/`ReactiveDict`), `ReactiveNode`, `ReactiveEdge`, `ReactiveReceivable`, `ReadonlyReactive`, `__reactive_members__` references that should have been renamed