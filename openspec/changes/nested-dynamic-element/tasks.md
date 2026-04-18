## 1. Core DynamicElement Changes

- [ ] 1.1 Modify `DynamicElement._get_node()` to traverse ancestor chain instead of raising — return the nearest non-DynamicElement ancestor's `_get_node()`. Remove `NoReturn` return type and `_init_node()` override.
- [ ] 1.2 Remove `DynamicElement._create_child_element()` override entirely (the only purpose was the nesting guard, which is no longer needed)
- [ ] 1.3 Verify `DynamicElement._node_count` and `_render_html` work correctly with nested DynamicElements (these are already recursive/sum-based, likely no changes needed)

## 2. RepeatElement and SwitchElement Compatibility

- [ ] 2.1 Verify `RepeatElement._refresh()` and `_reconcile_children()` work with nested DynamicElements — `self._parent._get_node()` should now traverse through DynamicElement ancestors correctly
- [ ] 2.2 Verify `SwitchElement._refresh()` works with nested DynamicElements — same `_get_node()` traversal fix applies
- [ ] 2.3 Verify `_remove_element()` cascade correctly cleans up nested DynamicElement callbacks (already recursive in `ElementWithChildren`, likely no changes needed)

## 3. Unit Tests

- [ ] 3.1 Add unit test: `repeat` inside `switch` renders correctly and updates on condition change
- [ ] 3.2 Add unit test: `switch` inside `repeat` template renders correctly per item
- [ ] 3.3 Add unit test: nested `repeat` inside `repeat` with keyed reconciliation
- [ ] 3.4 Add unit test: nested DynamicElement cleanup — verify reactive callbacks are removed when parent `switch` switches branches
- [ ] 3.5 Add unit test: `_get_node()` ancestor traversal for nested DynamicElements

## 4. E2E Tests

- [ ] 4.1 Create E2E test page: `repeat` inside `switch` (conditional list rendering)
- [ ] 4.2 Create E2E test page: `switch` inside `repeat` (per-item conditional rendering)
- [ ] 4.3 Write Playwright E2E test for switch-in-repeat pattern (interact with nested elements, verify DOM updates)

## 5. Lint, Type Check, and CI

- [ ] 5.1 Run `ruff check`, `ruff format`, and `pyright` — fix any issues
- [ ] 5.2 Run full test suite (`pytest tests/`) and verify all tests pass
- [ ] 5.3 Verify SSR rendering produces correct HTML for nested DynamicElements