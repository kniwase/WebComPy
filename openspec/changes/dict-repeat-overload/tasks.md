## 1. DictMutation Data Model

- [x] 1.1 Create `DictMutation` dataclass in `webcompy/reactive/_dict.py` with fields `op: str`, `key: str | int | None`, `value: Any`
- [x] 1.2 Add `_last_mutation: DictMutation | None` attribute to `ReactiveDict.__init__()`
- [x] 1.3 Set `_last_mutation` on `__setitem__` (op=`"set"`, key, value)
- [x] 1.4 Set `_last_mutation` on `__delitem__` (op=`"delete"`, key, value of deleted item)
- [x] 1.5 Set `_last_mutation` on `pop` (op=`"pop"`, key, popped value)
- [x] 1.6 Set `_last_mutation` on `clear` (op=`"clear"`, key=None, value=None)
- [x] 1.7 Export `DictMutation` from `webcompy/reactive/__init__.py`

## 2. Unit Tests for DictMutation

- [x] 2.1 Create `tests/test_dict_mutation.py` with test cases for each mutation op (`set`, `delete`, `pop`, `clear`)
- [x] 2.2 Add test that `on_after_updating` callback still receives full dict value (not DictMutation)
- [x] 2.3 Add test that `_last_mutation` is `None` after construction and updated after each mutation

## 3. RepeatElement Dict Mode

- [x] 3.1 Add `_is_dict: bool` flag to `RepeatElement.__init__()` that detects `ReactiveDict` input
- [x] 3.2 Store dict-mode template (`Callable[[K, V], ChildNode]`) alongside list-mode template
- [x] 3.3 Update `_generate_children()` to iterate `dict.items()` and call template with `(key, value)` when in dict mode
- [x] 3.4 Update `_populate_key_map()` to use dict keys (no key function needed) when in dict mode
- [x] 3.5 Update `_reconcile_children()` to iterate `dict.items()` and use dict keys for reconciliation when in dict mode
- [x] 3.6 Update `_refresh()` to pass correct arguments for dict mode

## 4. repeat() Function Overload

- [x] 4.1 Add `@overload` signature for `repeat(ReactiveDict, Callable[[K, V], ChildNode])` in `generators.py`
- [x] 4.2 Update `RepeatElement.__init__` type annotations to accept `ReactiveDict[K, V]`
- [x] 4.3 Verify no `key` parameter is accepted when `sequence` is a `ReactiveDict` (raise if passed)

## 5. Unit Tests for Dict Repeat

- [x] 5.1 Add tests for `RepeatElement` with `ReactiveDict` input in `tests/test_keyed_repeat.py`
- [x] 5.2 Test rendering dict entries, adding entries, deleting entries, clearing dict
- [x] 5.3 Test that dict keys are used as reconciliation identifiers (no separate key function)
- [x] 5.4 Test that template receives `(key, value)` in dict mode
- [x] 5.5 Add dict-mode tests to `tests/test_repeat.py` for basic rendering

## 6. E2E Tests

- [ ] 6.1 Create `tests/e2e/app/pages/dict_repeat.py` with a component using `ReactiveDict` + `repeat()`
- [ ] 6.2 Create `tests/e2e/test_dict_repeat.py` with Playwright tests for add/delete/clear/reorder scenarios
- [ ] 6.3 Update `tests/e2e/app/router.py` to include `/dict-repeat` route
- [ ] 6.4 Test that input values are preserved when adding/removing dict entries

## 7. Docs Examples Update

- [ ] 7.1 Refactor `docs_src/templates/demo/fizzbuzz.py` to use `ReactiveDict[int, str]` with keyed repeat
- [ ] 7.2 Refactor `docs_src/templates/demo/todo.py` to use `ReactiveDict[str, TodoData]` with UUID4 keys and keyed repeat
- [ ] 7.3 Update corresponding page components if needed

## 8. Lint, Type Check, and Final Verification

- [ ] 8.1 Run `uv run ruff check .` and fix any issues
- [ ] 8.2 Run `uv run ruff format .` and fix formatting
- [ ] 8.3 Run `uv run pyright` and fix type errors
- [ ] 8.4 Run `uv run python -m pytest tests/ --tb=short` and ensure all tests pass