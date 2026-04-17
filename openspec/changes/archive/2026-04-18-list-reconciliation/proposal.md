## Why

Every mutation to a `ReactiveList` triggers a full teardown and rebuild of all child elements in `RepeatElement`. Appending one item to a list of 100 causes 100 DOM removals + 101 DOM insertions. This makes list-heavy UIs impractically slow and destroys all element-local state (focus, scroll position, input values, animations) on every mutation. Key-based reconciliation is the standard solution in every major reactive UI framework (React, Vue, SolidJS, Svelte).

## What Changes

- Add a `key` function parameter to `repeat()` and `RepeatElement` that extracts a unique identifier from each list item
- Change `ReactiveList` change notifications to include granular mutation metadata (operation type, affected indices) alongside the full-value callback
- Reimplement `RepeatElement._refresh` to reconcile children using keys: reuse existing elements for unchanged keys, create new elements for added keys, remove elements for removed keys, and reorder when keys shift positions
- Update `_change_event` on `ReactiveList` methods to pass a `ListMutation` descriptor to after-update callbacks in addition to the existing full-value callback

## Capabilities

### New Capabilities
- `list-reconciliation`: Key-based reconciliation for `repeat()` that reuses existing DOM elements when list items change, move, or are added/removed, instead of rebuilding all children

### Modified Capabilities
- `reactive`: `ReactiveList` change notifications will carry granular mutation metadata (operation type, index, affected items) so that consumers can perform incremental updates
- `elements`: `repeat()` API gains an optional `key` function parameter; `RepeatElement._refresh` performs key-based reconciliation instead of full rebuild

## Impact

- **API**: `repeat()` gains an optional `key` parameter — backward compatible (existing code without `key` will fall back to full rebuild behavior)
- **ReactiveList**: Internal change to what `_change_event` passes to after-update callbacks — the callback signature for `ReactiveList` observers changes from `(new_value: list[V])` to `(new_value: list[V], mutation: ListMutation)`; the existing `on_after_updating` callbacks that only consume one positional arg will continue to work via `*args` pattern, but this needs verification
- **RepeatElement**: Complete rewrite of `_refresh` method; `_index_map` attribute (currently unused) will be repurposed for key-to-child mapping
- **Tests**: Unit tests in `tests/test_repeat.py` need updating for new reconciliation behavior; E2E tests in `tests/e2e/test_repeat.py` should gain new test cases for key-based scenarios (reorder, mid-list insert, state preservation)
- **Docs**: `docs_src` documentation for `repeat()` needs updating to document the `key` parameter

## Known Issues Addressed

- **No key-based reconciliation for list rendering** — RepeatElement rebuilds all children on change
- **No element-level reactivity in ReactiveList** — any mutation triggers full change notification (partially addressed: mutation metadata enables consumers to do incremental updates)

## Non-goals

- Do not implement virtual DOM diffing — this change only adds key-based reconciliation for `RepeatElement`
- Do not remove the existing full-rebuild fallback (lists without keys will continue to rebuild all children)
- Do not implement keyed reconciliation for `ReactiveDict` — dicts are not rendered as ordered lists
- Do not allow nested `DynamicElement` — that is a separate architectural change
- Do not change the `ReactiveList` public API surface beyond notification metadata (no new public methods)
- Do not implement move detection/optimization in the first iteration — moves will be handled as remove+insert, which is still far better than full rebuild