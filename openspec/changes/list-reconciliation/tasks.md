## 1. ListMutation Data Model

- [x] 1.1 Create `ListMutation` dataclass in `webcompy/reactive/_list.py` with fields: `op: str`, `index: int | None`, `value: Any`
- [x] 1.2 Add `_last_mutation: ListMutation | None` attribute to `ReactiveList.__init__`, initialized to `None`
- [x] 1.3 Set `_last_mutation` at the end of each mutating method body (`append`, `extend`, `pop`, `insert`, `sort`, `remove`, `clear`, `reverse`, `__setitem__`) with the correct `op`, `index`, and `value`

## 2. Unit Tests for ListMutation

- [x] 2.1 Create `tests/test_list_mutation.py` with tests verifying `_last_mutation` metadata for each `ReactiveList` mutation method (`append`, `extend`, `pop`, `insert`, `sort`, `remove`, `clear`, `reverse`, `__setitem__`)
- [x] 2.2 Test that `_last_mutation` is `None` on a freshly initialized `ReactiveList` (no mutations yet)
- [x] 2.3 Test that existing `on_after_updating` callbacks on `ReactiveList` still receive the same arguments (contract unchanged)

## 3. RepeatElement Key Support

- [x] 3.1 Add `key: Callable[[T], str | int] | None = None` parameter to `RepeatElement.__init__` and store as `self._key`
- [x] 3.2 Add `key: Callable[[T], str | int] | None = None` parameter to `repeat()` in `webcompy/elements/generators.py` and pass through to `RepeatElement`
- [x] 3.3 Initialize `self._key_to_child: dict[str | int, ElementAbstract]` and `self._children_keys: list[str | int]` in `RepeatElement.__init__`
- [x] 3.4 Populate `_key_to_child` and `_children_keys` in `_generate_children` and `_on_set_parent` when `self._key` is not `None`

## 4. Reconciliation Algorithm

- [x] 4.1 Implement `_reconcile_children` method on `RepeatElement` that: (a) builds `new_keys` list by mapping `self._key` over the new list value, (b) detects duplicate keys and raises `WebComPyException`, (c) determines which children to reuse, remove, and create
- [x] 4.2 Implement DOM reordering within `_reconcile_children`: detach surviving nodes, then re-insert all children (surviving + new) in the correct order using `insertBefore`
- [x] 4.3 Implement child removal: for keys present in old but absent in new, call `_remove_element` on the corresponding child
- [x] 4.4 Implement new child creation: for keys absent in old but present in new, generate child via `self._template(item)`, create element, and insert at correct position
- [x] 4.5 Update `RepeatElement._refresh` to call `_reconcile_children` when `self._key` is not `None`, and fall back to the current full-rebuild logic when `self._key` is `None`

## 5. Unit Tests for Reconciliation

- [x] 5.1 Test keyed `RepeatElement` with `append` — existing children not removed/recreated, new child appended
- [x] 5.2 Test keyed `RepeatElement` with `pop` — only the popped child removed, others preserved
- [x] 5.3 Test keyed `RepeatElement` with `insert` (mid-list) — existing children preserved, new child inserted at correct position
- [x] 5.4 Test keyed `RepeatElement` with `reverse` — children reordered in DOM, no children removed or created
- [x] 5.5 Test keyed `RepeatElement` with `clear` — all children removed
- [x] 5.6 Test duplicate keys raise `WebComPyException`
- [x] 5.7 Test unkeyed `RepeatElement` still does full rebuild (backward compatibility)

## 6. E2E Tests for Reconciliation

- [x] 6.1 Add keyed repeat page to e2e test app (`tests/e2e/app/pages/repeat.py`) with a `key` function on the repeat, along with add/remove/reorder buttons
- [x] 6.2 Add test: appending items to a keyed list preserves existing DOM nodes (check that existing item text remains unchanged)
- [x] 6.3 Add test: removing an item from a keyed list removes only that item's DOM node
- [x] 6.4 Add test: inserting at beginning/middle of a keyed list inserts at correct position
- [x] 6.5 Add test: input value in a list item is preserved after appending a new item (state preservation)

## 7. Update Existing Tests

- [x] 7.1 Review and update `tests/test_repeat.py` unit tests to account for new `key` parameter on `RepeatElement` and `repeat()`
- [x] 7.2 Review and update `tests/e2e/test_repeat.py` E2E tests — ensure existing unkeyed repeat tests still pass
- [x] 7.3 Update `tests/test_elements.py` if any repeat-related tests need adjusting

## 8. Type Annotations and Exports

- [x] 8.1 Export `ListMutation` from `webcompy/reactive/__init__.py` if it should be public, or keep it internal
- [x] 8.2 Update type annotations for `repeat()` and `RepeatElement.__init__` with the `key` parameter type
- [x] 8.3 Run `uv run pyright` and fix any type errors
- [x] 8.4 Run `uv run ruff check .` and `uv run ruff format .` to ensure linting/formatting passes