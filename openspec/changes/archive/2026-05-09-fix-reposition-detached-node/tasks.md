## 1. Fix _reposition_node

- [x] 1.1 In `_reposition_node()` at `_dynamic.py:74`, after the `if not parent:` early return, add a fallback that resolves the parent from `element._parent._get_node()` when the element is not a `DynamicElement`
- [x] 1.2 Guard the fallback path against `DynamicElement` instances (which have no DOM node of their own) with an `isinstance` check

## 2. Add tests

- [x] 2.1 Add unit test in `tests/test_switch_patch.py` for `_reposition_node` when the node's `parentNode` is `null` (simulating external DOM mutation)
- [x] 2.2 Verify all existing tests pass (`tests/test_switch_patch.py`, `tests/test_switch.py`, `tests/test_nested_dynamic.py`)
- [x] 2.3 Verify existing e2e tests pass (`tests/e2e/test_switch.py`, `tests/e2e/test_router.py`, `tests/e2e/test_nested_dynamic.py`)

## 3. Verification

- [x] 3.1 Run `uv run ruff check .` — no lint errors
- [x] 3.2 Run `uv run pyright` — no type errors
- [x] 3.3 Run `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs` — all tests pass
