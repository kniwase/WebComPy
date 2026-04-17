## Why

ReactiveDict currently has no element-level change notification — any mutation triggers a full-collection change, and `repeat()` only accepts `ReactiveList`. This means developers working with key-value data (todo items with UUIDs, number-keyed maps) must either convert to a list and lose element-level updates, or accept full rebuilds on every change. Adding `DictMutation` metadata and a `repeat()` overload for `ReactiveDict` enables keyed reconciliation for dict data, preserving DOM state (input values, focus) when individual entries are added, removed, or updated.

## What Changes

- Add `DictMutation` dataclass to `webcompy/reactive/_dict.py` with operation types: `set`, `delete`, `pop`, `clear`, `update`
- Set `_last_mutation` on each `ReactiveDict` mutating method (`__setitem__`, `__delitem__`, `pop`, `clear`) so incremental consumers can inspect what changed
- Add `repeat()` overload accepting `ReactiveDict[K, V]` with a template signature `(K, V) -> ChildNode`, where K (str | int) is used as the reconciliation key and V is the rendered value
- `RepeatElement` shall detect `ReactiveDict` input, iterate key-value pairs, and perform keyed reconciliation based on dict keys (no separate `key` function needed — the dict key IS the reconciliation key)
- Update FizzBuzz demo to use `ReactiveDict[int, str]` with keys as reconciliation keys
- Update ToDo List demo to use `ReactiveDict[str, TodoData]` with UUID4 keys for efficient checkbox state preservation
- Add unit tests for `DictMutation` metadata
- Add unit tests for `RepeatElement` with `ReactiveDict`
- Add E2E test for keyed dict repeat

## Capabilities

### New Capabilities
- `dict-repeat-overload`: DictMutation metadata model and repeat() overload for ReactiveDict with keyed reconciliation

### Modified Capabilities
- `reactive`: Adding DictMutation metadata and _last_mutation attribute to ReactiveDict
- `elements`: Extending repeat() to accept ReactiveDict and extending list rendering requirements for dict iteration
- `list-reconciliation`: Extending reconciliation to support dict-based keyed iteration

## Known Issues Addressed

- "No element-level reactivity in ReactiveList/ReactiveDict — any mutation triggers full change notification" — ReactiveDict now exposes `_last_mutation` metadata for incremental consumers, matching the pattern already established for ReactiveList

## Non-goals

- Making `ReactiveDict.__getitem__` reactive at the individual-key level (full-collection notification remains the default)
- Adding `update()` as a mutating method with DictMutation tracking (can be added later)
- Changing the existing `repeat(ReactiveList, template, key=)` API or behavior
- Providing dict-specific reconciliation optimizations beyond what the existing keyed reconciliation already supports (dict keys are the reconciliation keys, so the algorithm reuses the same path)

## Impact

- **webcompy/reactive/_dict.py**: Add `DictMutation` dataclass, `_last_mutation` tracking on mutating methods
- **webcompy/reactive/__init__.py**: Export `DictMutation`
- **webcompy/elements/generators.py**: Add dict overload to `repeat()`, update type aliases
- **webcompy/elements/types/_repeat.py**: Handle `ReactiveDict` in `RepeatElement.__init__`, `_render`, `_refresh`, `_reconcile_children`
- **docs_src/templates/demo/fizzbuzz.py**: Refactor to use `ReactiveDict`
- **docs_src/templates/demo/todo.py**: Refactor to use `ReactiveDict` with UUID4 keys
- **Tests**: New and updated test files