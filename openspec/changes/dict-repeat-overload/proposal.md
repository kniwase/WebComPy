## Why

ReactiveDict currently has no element-level change notification — any mutation triggers a full-collection change, and `repeat()` only accepts `ReactiveList`. This means developers working with key-value data (todo items with UUIDs, number-keyed maps) must either convert to a list and lose element-level updates, or accept full rebuilds on every change. Adding `DictMutation` metadata and a `repeat()` overload for `ReactiveDict` enables keyed reconciliation for dict data, preserving DOM state (input values, focus) when individual entries are added, removed, or updated.

## What Changes

- Add `DictMutation` dataclass to `webcompy/reactive/_dict.py` with operation types: `set`, `delete`, `pop`, `clear`
- Set `_last_mutation` on each `ReactiveDict` mutating method (`__setitem__`, `__delitem__`, `pop`, `clear`) so incremental consumers can inspect what changed
- Add `repeat()` overloads for `ReactiveDict[K, V]` with template signatures `(V,) -> ChildNode` (value only) and `(V, K) -> ChildNode` (value + key), where K (str | int) is used as the reconciliation key
- Add `repeat()` overloads for `ReactiveList[V]` with template signatures `(V,) -> ChildNode` (unkeyed, backward compatible), `(V, int) -> ChildNode` (indexed), and `(V, K) -> ChildNode` with key function
- `RepeatElement` shall detect `ReactiveDict` input and use `_two_arg_template` / `_single_arg_template` dispatch with `_call_template(v, k)` for unified invocation
- Update FizzBuzz demo to use `ReactiveDict[int, str]` with keys as reconciliation keys
- Update ToDo List demo to use `ReactiveDict[str, TodoData]` with UUID4 keys for efficient checkbox state preservation
- Add unit tests for `DictMutation` metadata
- Add unit tests for `RepeatElement` with `ReactiveDict`
- Add E2E test for keyed dict repeat

## Capabilities

### New Capabilities
- `dict-repeat-overload`: DictMutation metadata model and repeat() overloads for ReactiveDict and keyed ReactiveList with type-safe 5-overload API

### Modified Capabilities
- `reactive`: Adding DictMutation metadata and _last_mutation attribute to ReactiveDict
- `elements`: Extending repeat() with 5 type-safe overloads: dict single-arg, dict two-arg, list unkeyed, list indexed, list keyed
- `list-reconciliation`: Extending reconciliation to support dict-based keyed iteration and unified (V, K) template dispatch

## Known Issues Addressed

- "No element-level reactivity in ReactiveList/ReactiveDict — any mutation triggers full change notification" — ReactiveDict now exposes `_last_mutation` metadata for incremental consumers, matching the pattern already established for ReactiveList

## Non-goals

- Making `ReactiveDict.__getitem__` reactive at the individual-key level (full-collection notification remains the default)
- Adding `update()` as a mutating method with DictMutation tracking (can be added later)
- Providing dict-specific reconciliation optimizations beyond what the existing keyed reconciliation already supports (dict keys are the reconciliation keys, so the algorithm reuses the same path)

## Impact

- **webcompy/reactive/_dict.py**: Add `DictMutation` dataclass, `_last_mutation` tracking on mutating methods
- **webcompy/reactive/__init__.py**: Export `DictMutation`
- **webcompy/elements/generators.py**: Add 5 `@overload` signatures to `repeat()`, update type aliases
- **webcompy/elements/types/_repeat.py**: Add 5 `@overload` signatures to `RepeatElement.__init__`, refactor internal dispatch with `_two_arg_template` / `_single_arg_template` / `_call_template(v, k)`
- **docs_src/templates/demo/fizzbuzz.py**: Refactor to use `ReactiveDict`
- **docs_src/templates/demo/todo.py**: Refactor to use `ReactiveDict` with UUID4 keys
- **Tests**: New and updated test files