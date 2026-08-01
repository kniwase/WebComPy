# Tasks: fix-node-index-base-consistency

## 1. Core fix

- [x] 1.1 B1 — `ElementWithChildren._render` in `packages/webcompy/src/webcompy/elements/types/_base.py` (line ~38): change the child index base from `self._node_idx` to `0` while keeping the cumulative-offset accumulator (`idx = 0; for child: child._node_idx = idx; idx += child._node_count`). Coordinate with `fix-dynamic-child-node-index` if it has already landed the cumulative form there (amend only the base `self._node_idx` → `0`)
- [x] 1.2 B2 — base-aware `_re_index_children`. Adopted the implementation already shipped by #219 (`ElementWithChildren._re_index_children` dispatches on the receiver's kind: `getattr(self, "_node_idx", 0)` for `DynamicElement`, `0` otherwise) in place of design D2's proposed `DynamicElement` override — behaviorally equivalent and keeps the `getattr` fallback for `_node_idx`-less `FragmentElement`s. Verified by the offset-0/no-`_node_idx` tests (`TestReindexWithoutNodeIdx`) and by tasks 2.2–2.4
- [x] 1.3 Audit `_re_index_children` call sites for base correctness: `ElementWithChildren._hydrate_node` (`_base.py:48`), `_insert_child` (`:118`), `_pop_child` (`:124`), `RouterView._on_set_parent` (`router/_view.py:23`), `SwitchElement._refresh` (`_switch.py:112`), `MarkdownForElement._refresh` (`template/_markdown_for.py:524`). Confirm each now keys off the correct base via the receiver's kind (D2). No code change should be needed at the call sites; document the audit result in the commit message

## 2. Regression tests

- [x] 2.1 Add `tests/test_node_index_base_consistency.py`: a regular element at `_node_idx >= 1` containing a dynamic child (`{% for %}` over `ReactiveList`) followed by static siblings — after a signal-driven refresh (append/pop), the static siblings remain in the correct order (spec scenario "Non-zero-offset regular element preserves trailing siblings after refresh"). Verify RED before the fix
- [x] 2.2 Same file: dynamic container at non-zero offset (constructed directly or via a `RouterView`-analog) re-renders children positioned at the correct cumulative offset within the parent's node (spec scenario "Dynamic container at non-zero offset repositions children within its parent's node")
- [x] 2.3 Same file: `RouterView`-style pattern — a `SwitchElement` inside a dynamic parent at non-zero offset toggled multiple times preserves the preceding sibling's DOM node (spec scenario "RouterView-style dynamic parent preserves preceding siblings across toggles")
- [x] 2.4 Same file: re-indexing a dynamic parent at offset 0 yields the same indices as today (regression guard, spec scenario "Re-indexing a dynamic parent at offset 0 is unchanged")

## 3. Verification

- [ ] 3.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [ ] 3.2 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 3.3 Run full e2e suite via `scripts/run-e2e-tests.sh` (all groups, prod + static) and confirm all pass — especially the router and docs-e2e groups
- [ ] 3.4 Run `openspec validate fix-node-index-base-consistency`