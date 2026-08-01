# Tasks: fix-dynamic-child-node-index

## 1. Core fix

- [x] 1.1 Fix `ElementWithChildren._render` in `packages/webcompy/src/webcompy/elements/types/_base.py` (line ~38-39): replace enumerate-index assignment with cumulative-offset loop (`idx = self._node_idx; ...; idx += child._node_count`)
- [x] 1.2 Fix `DynamicElement._render` in `packages/webcompy/src/webcompy/elements/types/_dynamic.py` (line ~66-69): same cumulative-offset pattern
- [x] 1.3 Fix `ClientOnlyElement._hydrate_node` in `packages/webcompy/src/webcompy/elements/types/_client_only.py` (line ~47-48): same cumulative-offset pattern
- [x] 1.4 Fix `SwitchElement._render` and `SwitchElement._refresh` (two sites) in `packages/webcompy/src/webcompy/elements/types/_switch.py` (lines ~61-63, ~85-87, ~100-102): same cumulative-offset pattern
- [x] 1.5 Fix `RepeatElement._refresh` regenerate path and `RepeatElement._reconcile_children` in `packages/webcompy/src/webcompy/elements/types/_repeat.py` (lines ~162-164, ~204-205): cumulative-offset loop; in `_reconcile_children` advance a running `node_offset` by each child's `_node_count` instead of `node_offset + c_idx`
- [x] 1.6 Fix both assignment sites in `packages/webcompy/src/webcompy/elements/types/_suspense.py` (lines ~169-171, ~187-189): same cumulative-offset pattern
- [x] 1.7 Fix `MarkdownForElement._render` and `MarkdownForElement._refresh` in `packages/webcompy/src/webcompy/template/_markdown_for.py` (lines ~487-488, ~514-515): same cumulative-offset pattern (overrides `DynamicElement._render`/`_refresh`)

## 2. Regression tests

- [x] 2.1 Add `tests/test_dynamic_child_node_index.py`: multi-line `{% for %}` over `ReactiveList` via TestRenderer renders all items on initial render (spec scenario 1)
- [x] 2.2 Same file: after `ReactiveList.pop(0)` refresh, DOM contains exactly the updated items in order (spec scenario 2)
- [x] 2.3 Same file: multi-element `{% if %}` branch toggles correctly (spec scenario 3)
- [x] 2.4 Same file: keyed `repeat` (or `ReactiveDict`) with fragment-producing templates positions children without overlapping `_node_idx` (spec scenario 4)
- [x] 2.5 `MarkdownForElement` with fragment children receives cumulative `_node_idx` in `_render` (TestRenderer or fake-browser pattern from `tests/test_markdown_for.py`)

## 3. Review follow-up fixes (D4–D7)

- [x] 3.1 `RepeatElement._on_set_parent` and `MarkdownForElement._on_set_parent` re-parent existing children (`child._parent = self._parent`) instead of regenerating, so the batch orphaned by component-root adoption cannot leak live signal callbacks (fixes `AttributeError` on repeated `{% if %}` toggles inside `{% for %}`)
- [x] 3.2 `TextElement._init_node`, `ElementBase._init_node`, `RawHTMLElement._init_node`: only remove the existing node at `_node_idx` when it is not framework-managed (`elif not getattr(existing_node, "__webcompy_node__", False)`), matching `NewLine._init_node` — preserves hydration mismatch replacement while stopping destruction of following siblings during refresh
- [x] 3.3 `_re_index_children` starts from `self._node_idx` when the container is a `DynamicElement` (lazy import), so the sibling re-index added for ClientOnly/Suspense materialization stays correct for nested dynamic parents
- [x] 3.4 `RepeatElement._reconcile_children`: remove the trailing-node cleanup that deleted following siblings; keep an explicit `child._node_cache is None → await child._render()` fallback in the merged loop
- [x] 3.5 Regression tests: reactive `{% if %}` inside reactive `{% for %}` toggled twice plus list mutations; repeat refresh with following sibling; nested for loops; keyed dict repeat with following sibling (spec scenarios 5–6)
- [x] 3.6 Align `tests/test_elements_browser.py::test_non_prerendered_text_node_removed_and_recreated` with browser semantics (`__webcompy_node__ = False` on the stale node)

## 4. Verification (follow-up)

- [x] 4.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [x] 4.2 Run `uv run python -m pytest tests/ --tb=short`
- [x] 4.3 Run e2e suite via `scripts/run-e2e-tests.sh` (all groups, prod + static) and confirm all pass
- [x] 4.4 Run `openspec validate fix-dynamic-child-node-index`

## 5. Review follow-up fixes (D5 test parity, D8)

- [x] 5.1 `FakeDOMNode.__setattr__` in `packages/webcompy-testing/src/webcompy_testing/_dom.py`: setting `__webcompy_prerendered_node__ = True` also clears `_webcompy_node`, mirroring browser prerendered-child marking (`_root_component._mark_as_prerendered`) so the `_init_node` mismatch branch is testable
- [x] 5.2 Add `tests/test_elements_browser.py::TestPartialHydrationElement::test_hydrate_replaces_prerendered_tag_mismatch`: a prerendered node whose tag does not match is removed and replaced by `_init_node` (browser parity)
- [x] 5.3 `DynamicElement.__init__` assigns `self._children = []` per instance (`packages/webcompy/src/webcompy/elements/types/_dynamic.py`), removing the shared-class-attribute reliance for all dynamic subclasses (design D8)
- [x] 5.4 Fix `ElementBase._render` naming to `ElementWithChildren._render` in the delta spec, proposal, design (Alternatives), and tasks 1.1
- [x] 5.5 Update design.md (D5 test-parity note, D8) and proposal.md (What Changes, Impact)

## 6. Verification (second follow-up)

- [x] 6.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [x] 6.2 Run `uv run python -m pytest tests/ --tb=short`
- [x] 6.3 Run e2e suite via `scripts/run-e2e-tests.sh` (relevant groups, prod + static) and confirm all pass
- [x] 6.4 Run `openspec validate fix-dynamic-child-node-index`

## 7. Verification

- [x] 7.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [x] 7.2 Run `uv run python -m pytest tests/ --tb=short`
- [x] 7.3 Run full e2e suite via `scripts/run-e2e-tests.sh` (all groups, prod + static) and confirm all pass
- [x] 7.4 Run `openspec validate fix-dynamic-child-node-index`

## 8. Review follow-up fixes (D9–D11)

- [x] 8.1 `_re_index_children` starts from `getattr(self, "_node_idx", 0)` when the container is a `DynamicElement` (`_base.py`), preventing `AttributeError` when `_node_idx` is unassigned (design D9 — `RouterView._on_set_parent` and other parent-first paths)
- [x] 8.2 `ElementAbstract._hydrate_node` removes the existing node only when it is not framework-managed (`elif not getattr(existing, "__webcompy_node__", False)`), matching the D5 `_init_node` guard (design D10)
- [x] 8.3 `MarkdownForElement._render` calls `self._parent._re_index_children(False)` after `_position_element_nodes`, matching `DynamicElement._render` (design D11)
- [x] 8.4 Regression tests: `_re_index_children` on a `FragmentElement` without `_node_idx` and on the `RouterView._on_set_parent` path; `_hydrate_node` preserves framework-managed nodes while still replacing prerendered tag mismatches; markdown-for `_render` corrects a stale following-sibling `_node_idx`
- [x] 8.5 Update design.md (D9–D11, plain-container base-convention future-work note) and proposal.md (What Changes, Non-goals, Impact)

## 9. Verification (third follow-up)

- [x] 9.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [x] 9.2 Run `uv run python -m pytest tests/ --tb=short`
- [x] 9.3 Run e2e suite via `scripts/run-e2e-tests.sh` (relevant groups: reactive-lists, dynamic-control, template, components, bootstrap-static; prod + static) and confirm all pass
- [x] 9.4 Run `openspec validate fix-dynamic-child-node-index`

## 10. Regression fix (D12)

- [x] 10.1 Add `DynamicElement._cancel_pending_render_tasks()` (extracted from `_remove_element`) and call it at the top of `RepeatElement._refresh`, `SwitchElement._refresh`, `MarkdownForElement._refresh`, and before `_patch_children` in `SuspenseElement._browser_resolve`/`_handle_error`; update design.md (D12), proposal.md, and spec delta
- [x] 10.2 Regression test: repeat hydration schedules render tasks, refresh cancels them, and no ghost nodes appear after the event loop runs (RED before fix, GREEN after)
- [x] 10.3 Verify: ruff/pyright, full unit suite, full e2e suite (all groups, prod + static), openspec validate
