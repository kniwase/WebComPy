## Context

WebComPy's `RepeatElement` currently tears down and rebuilds all children on every `ReactiveList` mutation. This is triggered by `ReactiveList`'s coarse-grained change notification system — every mutation method (`append`, `insert`, `pop`, `remove`, etc.) is decorated with `@ReactiveBase._change_event`, which calls `callback_after_updating(instance, return_value)` where `return_value` is the result of the mutation method (not the full list). `RepeatElement._refresh` receives this as `*args` but ignores it, performing a full rebuild regardless.

The `_index_map` attribute already exists on `RepeatElement` (line 19 of `_repeat.py`) but is declared and never populated — suggesting this was once planned but never implemented.

Current `ReactiveList` mutation methods return various types: `append` returns `None`, `pop` returns the popped item, `insert` returns `None`, etc. This inconsistency makes the return value unreliable for reconciliation.

```
Current flow:

  items.append("new")         items.pop(0)          items.insert(0, "x")
       │                           │                       │
       ▼                           ▼                       ▼
  @_change_event              @_change_event           @_change_event
  callback_before(old_list)  callback_before(old_list)  callback_before(old_list)
  append() → None             pop() → item              insert() → None
  callback_after(None)        callback_after(item)       callback_after(None)
       │                           │                       │
       ▼                           ▼                       ▼
  RepeatElement._refresh(*args) ←── all args ignored, full rebuild
```

## Goals / Non-Goals

**Goals:**
- Enable `RepeatElement` to reuse DOM elements when list items are added, removed, or reordered by matching keys
- Provide mutation metadata from `ReactiveList` so consumers can perform incremental updates
- Maintain backward compatibility: `repeat()` without a `key` function falls back to full rebuild
- Preserve element-local state (focus, input values, scroll position) when keys match

**Non-Goals:**
- Virtual DOM diffing for arbitrary element trees
- Keyed reconciliation for `ReactiveDict`
- Allowing nested `DynamicElement`
- Move optimization (moves will be handled as remove + insert — still O(n) better than full rebuild)
- Changing `ReactiveList`'s existing public method signatures

## Decisions

### 1. Mutation metadata via a dedicated `ListMutation` dataclass

**Decision**: Create a `ListMutation` dataclass that describes what operation occurred, at what index, and with what value.

```python
class ListMutation:
    op: Literal["append", "extend", "pop", "insert", "remove", "clear", "reverse", "sort", "setitem"]
    index: int | None
    value: Any
    old_value: Any
```

**Rationale**: The current `_change_event` decorator passes the method's return value to after-update callbacks, but this is inconsistent (`pop` returns the item, `append` returns `None`). A structured mutation descriptor gives `RepeatElement` (and any future consumer) the information needed for incremental updates.

**Alternative considered**: Store a diff of old vs. new list. Rejected because computing a diff for every mutation is O(n) and redundant — we already know the operation at the call site.

**Alternative considered**: Separate callback types per operation. Rejected because it would require changing the `ReactiveStore` callback architecture significantly. Using a single `ListMutation` parameter on the existing callback is simpler.

### 2. `_change_event` for ReactiveList methods will attach mutation metadata to the reactive instance

**Decision**: Each `ReactiveList` mutation method will set `self._last_mutation` before the `_change_event` callback fires. The after-update callback receives the full list value (as before) plus can read `_last_mutation`.

```python
# In ReactiveList
@ReactiveBase._change_event
def append(self, value: V):
    self._last_mutation = ListMutation(op="append", index=len(self._value) - 1, value=value, old_value=None)
    self._value.append(value)
```

Wait — this has ordering issues because `_change_event` calls `callback_before` before the method body runs. Let me reconsider.

**Revised Decision**: Override `_change_event` behavior for `ReactiveList` so that the mutation metadata is captured *inside* the decorated method and made available to the after-update callback. The cleanest approach: after the mutation method runs and before `callback_after_updating`, store the mutation on `self._last_mutation`. The after-update callback can then access it.

**Actual approach**: Create a custom decorator `_list_change_event` that wraps the method, captures mutation info after the method body, and passes it alongside the value to after-update callbacks.

Actually, the simplest approach: store `_last_mutation` on the ReactiveList instance at the end of each mutating method. Since `_change_event` calls `callback_after_updating` *after* the method body, and `callback_after_updating` passes the method's return value, we can change `ReactiveList` methods to return a `ListMutation` instead of their natural return value. But this breaks `pop()` which returns the popped value.

**Final Decision**: Add a `_last_mutation: ListMutation | None` attribute on `ReactiveList`. Each mutating method sets it before returning. The `_change_event` decorator's after-update callback will pass `self._value` (the full list) unchanged — this doesn't change. `RepeatElement._refresh` reads `self._sequence._last_mutation` as additional context for reconciliation.

```python
# ReactiveList.append
@ReactiveBase._change_event
def append(self, value: V):
    self._value.append(value)
    self._last_mutation = ListMutation(op="append", index=len(self._value) - 1, value=value)

# RepeatElement._refresh reads:
mutation = self._sequence._last_mutation
```

**Rationale**: This avoids changing the `ReactiveStore` callback contract at all. The `_change_event` decorator and `callback_after_updating` continue to work as before. Mutation metadata is a side channel that only `RepeatElement` reads.

### 3. Key function as optional parameter on `repeat()`

**Decision**: Add an optional `key: Callable[[T], str | int]` parameter to `repeat()` and `RepeatElement.__init__`.

```python
def repeat(
    sequence: ReactiveBase[list[T]],
    template: Callable[[T], ChildNode],
    key: Callable[[T], str | int] | None = None,
):
    return RepeatElement(sequence, template, key)
```

**Rationale**: Same pattern as Vue's `:key`, React's `key` prop, and Svelte's `#each items as item (key)`. The key function extracts a unique identifier from each item. When provided, reconciliation uses keys; when absent, full rebuild is used (backward compatible).

**Key type**: `str | int` — these are the only types that work as dict keys across both Python and JavaScript (important for PyScript compatibility) and are hashable for O(1) lookup.

### 4. Reconciliation algorithm

**Decision**: Use a key-to-child mapping approach:

```
1. Build old_keys = [key(item) for each current child]
2. Build new_keys = [key(item) for each item in new list]
3. Create key_to_child map from old children
4. For each new key in order:
   a. If key exists in key_to_child → reuse that child element
   b. If key does not exist → create new child element
5. Children whose keys are NOT in new_keys → remove those elements
6. Reorder DOM nodes to match new_keys order
```

**Rationale**: This is the simplest correct algorithm. It handles all cases (append, prepend, insert, remove, reorder) without needing a diffing algorithm like React's O(n) heuristic.

**Complexity**: O(n) where n = max(old_count, new_count). Building key maps is O(n), lookup is O(1), DOM operations are O(n) in the worst case (all reorder).

**Alternative considered**: Longest-increasing-subsequence (LIS) optimization for moves (like Vue 3). Rejected for first iteration — the remove+insert approach is simpler and already a massive improvement over full rebuild.

### 5. DOM reordering strategy

**Decision**: After determining the new child order, reattach all surviving children in sequence using `insertBefore` with the next reference node.

```
1. Detach all surviving children's nodes from the DOM
2. For each child in new order:
   a. If new child → render and insertBefore(next_node)
   b. If reused child → reattach node via insertBefore(next_node)
```

**Rationale**: Simply removing and re-inserting in the correct order is the most reliable approach. It avoids edge cases with `appendChild` not moving existing nodes.

**Alternative considered**: Targeted `insertBefore` moves only for out-of-order children. More complex, potentially fewer DOM operations, but harder to get right. Can be optimized later.

### 6. Full rebuild fallback when no key is provided

**Decision**: When `key` is `None`, `RepeatElement._refresh` continues to use the current full-rebuild behavior.

**Rationale**: This ensures backward compatibility. Applications that don't need reconciliation don't need to change anything. The full rebuild is simple and correct.

### 7. Duplicate key handling

**Decision**: If duplicate keys are detected at runtime, raise a `WebComPyException` with a clear message identifying the duplicate key values.

**Rationale**: Duplicate keys cause undefined reconciliation behavior (which child to reuse?). Failing fast is better than silent misbehavior. This matches React's behavior (warning in dev) and Vue's behavior (error for duplicate keys).

## Risks / Trade-offs

- **[Risk] Existing `on_after_updating` callbacks on ReactiveList may break** → Mitigation: The `_last_mutation` attribute is additive. The callback signature (`callback_after_updating(value)`) does not change. Existing callbacks will continue to work unchanged. `RepeatElement._refresh` currently accepts `*args` and ignores them, so adding the mutation channel is safe.

- **[Risk] Key function returning non-unique keys causes errors** → Mitigation: Runtime check for duplicate keys raises a clear exception. Developer is responsible for providing unique keys.

- **[Risk] Memory from `_last_mutation` if ReactiveList is used without RepeatElement** → Mitigation: `_last_mutation` is a single attribute, overwritten on each mutation. Memory cost is negligible.

- **[Risk] Reconciliation reorders all surviving DOM nodes even if only one was inserted** → Mitigation: This is correct but may cause unnecessary DOM mutations for simple appends. Future optimization: only reattach reordered nodes, not all surviving nodes.

- **[Trade-off] Move = remove + insert instead of actual DOM move** → This is simpler but may cause extra DOM operations for reordered lists. Acceptable for first implementation. An LIS-based optimization can be added later.

- **[Trade-off] `ListMutation` only carries the last mutation** → If multiple mutations fire before `_refresh` runs (e.g., in a synchronous loop), only the last mutation is captured. Mitigation: `_refresh` will fall back to full rebuild if the mutation metadata doesn't match the actual change (e.g., list length changed by more than the mutation implies).

## Open Questions

- Should `MultiLineTextElement` (which extends `RepeatElement`) use reconciliation? Currently it splits text into lines and wraps them in a `RepeatElement`. Keys could be line indices, but the overhead may not be worth it for text nodes. **Leaning toward: no key for MultiLineTextElement, keep full rebuild.**