## 1. Fix _patch_children offset

- [x] 1.1 Add `node_idx_offset: int = 0` parameter to `_patch_children()` signature in `webcompy/elements/types/_dynamic.py`
- [x] 1.2 Update `_reposition_node(new_child, new_idx)` call at line 109 to use `node_idx_offset + new_idx`
- [x] 1.3 Update `_reposition_node(new_child, new_idx)` call at line 123 to use `node_idx_offset + new_idx`

## 2. Update SwitchElement caller

- [x] 2.1 In `SwitchElement._refresh()` line 70, pass `self._node_idx` as third argument: `_patch_children(old_children, new_children, self._node_idx)`

## 3. Add tests

- [x] 3.1 Add unit test in `tests/test_switch_patch.py` for `_patch_children` with non-zero `node_idx_offset` and a preceding sibling DOM node
- [x] 3.2 Verify all existing tests pass (`tests/test_switch_patch.py`, `tests/test_switch.py`, `tests/test_nested_dynamic.py`)
- [x] 3.3 Verify existing e2e tests pass (`tests/e2e/test_switch.py`, `tests/e2e/test_router.py`, `tests/e2e/test_nested_dynamic.py`)

## 4. Verification

- [x] 4.1 Run `uv run ruff check .` — no lint errors
- [x] 4.2 Run `uv run pyright` — no type errors
- [x] 4.3 Run `uv run python -m pytest tests/ --tb=short` — all tests pass
