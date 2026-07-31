# Tasks: fix-dynamic-child-node-index

## 1. Core fix

- [ ] 1.1 Fix `ElementBase._render` in `packages/webcompy/src/webcompy/elements/types/_base.py` (line ~38-39): replace enumerate-index assignment with cumulative-offset loop (`idx = self._node_idx; ...; idx += child._node_count`)
- [ ] 1.2 Fix `DynamicElement._render` in `packages/webcompy/src/webcompy/elements/types/_dynamic.py` (line ~66-69): same cumulative-offset pattern
- [ ] 1.3 Fix `ClientOnlyElement._hydrate_node` in `packages/webcompy/src/webcompy/elements/types/_client_only.py` (line ~47-48): same cumulative-offset pattern
- [ ] 1.4 Fix `SwitchElement._render` and `SwitchElement._refresh` (two sites) in `packages/webcompy/src/webcompy/elements/types/_switch.py` (lines ~61-63, ~85-87, ~100-102): same cumulative-offset pattern
- [ ] 1.5 Fix `RepeatElement._refresh` regenerate path and `RepeatElement._reconcile_children` in `packages/webcompy/src/webcompy/elements/types/_repeat.py` (lines ~162-164, ~204-205): cumulative-offset loop; in `_reconcile_children` advance a running `node_offset` by each child's `_node_count` instead of `node_offset + c_idx`
- [ ] 1.6 Fix both assignment sites in `packages/webcompy/src/webcompy/elements/types/_suspense.py` (lines ~169-171, ~187-189): same cumulative-offset pattern
- [ ] 1.7 Fix `MarkdownForElement._render` and `MarkdownForElement._refresh` in `packages/webcompy/src/webcompy/template/_markdown_for.py` (lines ~487-488, ~514-515): same cumulative-offset pattern (overrides `DynamicElement._render`/`_refresh`)

## 2. Regression tests

- [ ] 2.1 Add `tests/test_dynamic_child_node_index.py`: multi-line `{% for %}` over `ReactiveList` via TestRenderer renders all items on initial render (spec scenario 1)
- [ ] 2.2 Same file: after `ReactiveList.pop(0)` refresh, DOM contains exactly the updated items in order (spec scenario 2)
- [ ] 2.3 Same file: multi-element `{% if %}` branch toggles correctly (spec scenario 3)
- [ ] 2.4 Same file: keyed `repeat` (or `ReactiveDict`) with fragment-producing templates positions children without overlapping `_node_idx` (spec scenario 4)
- [ ] 2.5 `MarkdownForElement` with fragment children receives cumulative `_node_idx` in `_render` (TestRenderer or fake-browser pattern from `tests/test_markdown_for.py`)

## 3. Verification

- [ ] 3.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [ ] 3.2 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 3.3 Run full e2e suite via `scripts/run-e2e-tests.sh` (all groups, prod + static) and confirm all pass
- [ ] 3.4 Run `openspec validate fix-dynamic-child-node-index`
