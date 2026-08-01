# Proposal: fix-dynamic-child-node-index

## Why

Dynamic container elements (`DynamicElement`, `RepeatElement`, `SwitchElement`, `SuspenseElement`, `ClientOnlyElement`, `MarkdownForElement`, and `ElementBase`) assign each child's `_node_idx` as `self._node_idx + c_idx` — the child's **position index** in the children list — instead of the **cumulative node offset** (sum of preceding siblings' `_node_count`). For single-node children the two are identical, so the defect is invisible. For multi-node children (`FragmentElement`, produced by any multi-line template body with whitespace text nodes), later children are positioned at wrong DOM indices, causing rendered nodes to be lost or misplaced: a reactive `{% for %}` with a multi-line body renders only its last item's element after a refresh, and a multi-element `{% if %}` branch misbehaves. This blocks idiomatic multi-line template bodies in reactive control flow and was found while verifying `feat-template-expression-language`.

## What Changes

- Replace index-based `_node_idx` assignment with cumulative node-offset assignment in all 12 sites across 7 files:
  - `elements/types/_base.py` (`ElementWithChildren._render`)
  - `elements/types/_dynamic.py` (`DynamicElement._render`)
  - `elements/types/_client_only.py` (`ClientOnlyElement._hydrate_node`)
  - `elements/types/_switch.py` (`SwitchElement._render`, `SwitchElement._refresh` ×2)
  - `elements/types/_repeat.py` (`RepeatElement._refresh` regenerate path, `RepeatElement._reconcile_children`)
  - `elements/types/_suspense.py` (`SuspenseElement` ×2)
  - `template/_markdown_for.py` (`MarkdownForElement._render`, `MarkdownForElement._refresh`)
- Add regression tests pinning multi-node-child positioning for reactive `{% for %}` (initial render and post-mutation refresh), multi-element `{% if %}` branch toggling, and keyed reconciliation with fragment children.
- Fix refresh-path defects exposed by the index fix: `RepeatElement._on_set_parent`/`MarkdownForElement._on_set_parent` re-parent existing children instead of regenerating them (prevents orphaned switch batches with live signal callbacks — see design D4); `TextElement`/`ElementBase`/`RawHTMLElement._init_node` only remove non-framework nodes at the element's index (prevents destruction of following siblings — design D5); `_re_index_children` starts from the container's own `_node_idx` for dynamic containers (design D6); `_reconcile_children` drops the sibling-eating trailing-node cleanup and keeps a full-render fallback for reused children with cleared node caches (design D7).
- Harden dynamic containers: `DynamicElement.__init__` assigns `self._children = []` per instance so no `DynamicElement` read (e.g., the `_on_set_parent` guard) falls back to the shared class attribute (design D8).
- Review-follow-up hardening (third round): `_re_index_children` falls back to 0 when a `DynamicElement`'s `_node_idx` is unassigned (design D9 — prevents `AttributeError` from `RouterView._on_set_parent` and other parent-first code paths); `ElementAbstract._hydrate_node` adopts the D5 framework-node guard so hydration no longer removes framework-managed nodes at the element's index (design D10); `MarkdownForElement._render` calls `self._parent._re_index_children(False)` for parity with `DynamicElement._render` (design D11).
- Align `FakeDOMNode` prerendered marking with browser semantics (`__webcompy_prerendered_node__ = True` also clears `_webcompy_node`, mirroring `_root_component._mark_as_prerendered`) so the `_init_node` mismatch-replacement branch is testable; add a regression test for replacing a prerendered node with a mismatched tag.
- Extend regression tests: reactive `{% if %}` inside reactive `{% for %}` toggled twice, repeat refresh with a following sibling, nested for loops, and keyed dict repeat with a following sibling.
- Cancel stale hydration render tasks in every refresh path that replaces children (`RepeatElement._refresh`, `SwitchElement._refresh`, `MarkdownForElement._refresh`, `SuspenseElement._browser_resolve`/`_handle_error`) via a shared `DynamicElement._cancel_pending_render_tasks()` helper extracted from `_remove_element` — a render task scheduled for a replaced child must not execute and re-insert its DOM nodes (fixes duplicated todo items in the docs demo, design D12).

No public API changes. Behavior is unchanged for single-node children (index and cumulative offset coincide).

## Capabilities

### New Capabilities

### Modified Capabilities

- `elements`: Add a normative requirement pinning cumulative child node indexing in dynamic containers, with regression scenarios for multi-node (`FragmentElement`) children in repeat/switch render and refresh paths.

## Known Issues Addressed

- **Multi-line template body + reactive control flow loses DOM nodes** (discovered during `feat-template-expression-language` verification): `{% for %}`/`{% if %}` whose bodies produce `FragmentElement` children render only the last fragment's elements after a refresh (and in `TestRenderer` even on initial render), because fragment children receive overlapping `_node_idx` values.
- **Reactive `{% if %}` inside a reactive `{% for %}` raises on repeated toggles** (found while verifying the initial fix): the second condition toggle threw `AttributeError` from `SwitchElement._refresh` and lost the last item, because component-root adoption assigns the repeat's parent twice and the first generated child batch (with registered signal callbacks and a broken parent chain) was never cleaned up.
- **Following siblings of a dynamic container are deleted on refresh** (found while verifying the initial fix): a `<span>` after a `{% for %}` disappeared after a list mutation, caused by the destructive `_get_existing_node()` removal in `_init_node` and a trailing-node cleanup in `_reconcile_children` that assumed the repeat's content extends to the end of the parent's child list.

## Non-goals

- Changes to the key-based reconciliation algorithm itself (key matching, reuse semantics).
- Changes to hydration/adopt behavior (`_hydrate_node` already uses cumulative indexing and was untouched except `ClientOnlyElement`, which used the buggy pattern; design D10 extends the D5 framework-node guard to the hydration mismatch fallback without changing adoption semantics).
- Whitespace-text-node elimination from template binding (fragments with text nodes remain valid input; this change makes containers handle them correctly).
- Any public API or spec-level behavior change beyond pinning the corrected positioning.

## Impact

- **Code**: `packages/webcompy/src/webcompy/elements/types/{_base,_dynamic,_client_only,_switch,_repeat,_suspense,_abstract}.py` and `packages/webcompy/src/webcompy/template/_markdown_for.py` — 12 mechanical edits, each replacing enumerate-index assignment with a cumulative-offset loop (the pattern already used by `_re_index_children`, `_hydrate_node`, `_position_element_nodes`, and `_append_child`); plus the refresh-path fixes in `_repeat.py`, `_markdown_for.py`, `_base.py` (`_re_index_children`), `_element.py`, and `_text.py` (`_init_node`), the `_children` initialization in `_dynamic.py`, the prerendered-marking alignment in `packages/webcompy-testing/src/webcompy_testing/_dom.py`, and the D9–D11 hardening in `_base.py`/`_abstract.py`/`_markdown_for.py`, all described under "What Changes".
- **Specs**: `openspec/specs/elements/spec.md` (delta: one ADDED requirement with extended scenarios).
- **Tests**: new regression tests in `tests/` (TestRenderer-based); full unit suite and full e2e suite re-run.
- **Risk**: low — for single-node children, cumulative offset equals child index, so existing behavior is preserved by construction; multi-node children previously produced broken DOM, so no working behavior depends on the current indexing. The `_init_node` guard (design D5) and the `_hydrate_node` guard (design D10) preserve prerendered-node replacement (hydration) and only stop removal of framework-managed nodes, matching the pre-existing `NewLine` behavior.
