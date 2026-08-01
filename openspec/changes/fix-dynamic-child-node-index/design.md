# Design: fix-dynamic-child-node-index

## Context

Element positioning in WebComPy relies on `_node_idx`: every `ElementAbstract` knows its start index within its parent's DOM `childNodes`. Dynamic containers (elements without their own DOM node — `DynamicElement` subclasses such as `RepeatElement`, `SwitchElement`, `FragmentElement`, `SuspenseElement`, `ClientOnlyElement`, and `MarkdownForElement` (which overrides `_render`/`_refresh`), plus the `_render` loop of `ElementBase`) assign children's `_node_idx` before rendering and rely on `_position_element_nodes` to insert/move DOM nodes at those indices.

The codebase already contains the correct cumulative-offset pattern in four places:

- `ElementWithChildren._re_index_children` (`_base.py:98-102`): `idx += child._node_count`
- `DynamicElement._hydrate_node` (`_dynamic.py:92-94`): `idx += child._node_count`
- `_position_element_nodes` (`_dynamic.py:206-210`): recursive cumulative walk
- `ElementWithChildren._append_child` (`_base.py:109`): last child's `node_idx + node_count`

However, 12 sites across 7 files assign `child._node_idx = self._node_idx + c_idx` (enumerate index). When every child has `_node_count == 1` (plain `Element`/`TextElement`), enumerate index equals cumulative offset, so the defect is invisible. When a child is a `FragmentElement` (multi-node — produced by template binding of multi-line bodies, since whitespace becomes `TextElement` siblings), subsequent children get indices that overlap earlier siblings' node ranges, and `insertBefore` positioning corrupts the DOM: earlier fragments' element nodes end up detached, leaving only the last fragment's elements.

Reproduction (verified on the base commit and via monkey-patched fix):

- Multi-line `{% for item in items %}` over a `ReactiveList`: `TestRenderer` initial render shows only the last `<li>`; in the browser, initial hydration works (hydration uses cumulative indexing) but post-mutation refresh drops all but the last item.
- The monkey-patched fix (cumulative assignment in `DynamicElement._render` and `RepeatElement._refresh`) makes initial render, refresh reconciliation, and `{% if %}` fragment-branch toggling all pass.

## Goals / Non-Goals

**Goals:**

- Assign `_node_idx` by cumulative node offset in every dynamic container child loop
- Pin the behavior with regression tests (multi-node children in repeat initial render, repeat refresh, if-branch toggle, keyed reconciliation)
- Zero behavior change for single-node children

**Non-Goals:**

- Reconciliation algorithm changes; hydration path changes; whitespace filtering in template binding
- Any public API change

> Note: D4–D11 below are implementation-level fixes discovered during review of the initial cumulative-indexing change. They are required for the change's stated goal (correct DOM after refresh) or harden the implementation against review findings, and are not spec-level behavior changes; the delta spec scenarios are extended accordingly.

## Decisions

### D1: Apply the existing cumulative pattern verbatim to all 12 sites

Each buggy loop becomes:

```python
idx = self._node_idx
for child in self._children:
    child._node_idx = idx
    idx += child._node_count
    ...  # existing per-child logic (render / position) unchanged
```

For `RepeatElement._reconcile_children` (`_repeat.py:204-205`), `node_offset + c_idx` becomes a running `node_offset += child._node_count` per iteration (children not reused still render afterward at their assigned index).

`MarkdownForElement` (`template/_markdown_for.py`) overrides `DynamicElement._render` and `_refresh` with the same enumerate-index pattern; its children (produced via `_render_nodes` → `bind_children`) may include `SwitchElement`/`RepeatElement`/components, i.e., multi-node children, so the same two sites receive the cumulative fix.

No helper extraction: the loop is 3 lines and the four existing correct sites already inline it; a shared helper can be introduced later if the pattern grows.

*Alternatives considered*: (a) Fixing only `RepeatElement` — rejected: `SwitchElement._render/_refresh`, `SuspenseElement`, `ClientOnlyElement._hydrate_node`, `MarkdownForElement._render/_refresh`, `ElementWithChildren._render`, and `DynamicElement._render` share the identical defect and all accept fragment children (e.g., a switch branch whose generator returns multiple elements, a plain element containing a fragment child). (b) Changing `_position_element_nodes` to tolerate wrong indices — rejected: treats the symptom, leaves `_node_idx` semantics broken for reconciliation and `_children_length` arithmetic.

### D2: Regression tests via `TestRenderer` with multi-line templates

Multi-line template bodies are the minimal, realistic reproducer (whitespace text nodes force `FragmentElement` children). Tests assert the rendered `<li>`/`<p>` text sequences after initial render and after signal-driven refresh, following existing `TestRenderer` patterns from `tests/test_template_ssr.py`.

### D3: Fix is normative-pinned in the `elements` spec as an ADDED requirement

The existing requirements already describe the intended rendering behavior ("render all items", "display one branch"); this defect is an implementation violation, not a spec ambiguity. One ADDED requirement pins cumulative indexing explicitly so future container loops are reviewed against it.

### D4: `_on_set_parent` re-parents existing children instead of regenerating them

`RepeatElement._on_set_parent` and `MarkdownForElement._on_set_parent` originally replaced `self._children` with a fresh `_generate_children()` on every parent assignment. Because component-root adoption (`Component.__init_component` → `_init_children`) assigns the repeat's parent twice (template root element → component), the first generated batch was orphaned with its signal callbacks still registered — a leaked `SwitchElement` inside a discarded batch kept refreshing on condition toggles with a broken parent chain, raising `AttributeError` in `_refresh`. The fix: when children already exist, re-parent them to the new parent (`child._parent = self._parent`, which cascades through `FragmentElement._on_set_parent`) and return; only generate on the first parent assignment. This eliminates the orphan batch and its live callbacks without touching the DOM.

### D5: `_init_node` removes only non-framework nodes at the element's index

`TextElement._init_node`, `ElementBase._init_node`, and `RawHTMLElement._init_node` removed *any* existing node found at `_node_idx` (via `_get_existing_node`) that did not match a prerendered node — including nodes owned by *other* elements (e.g., a sibling following a dynamic container). On refresh, mounting new children at their (now correct) cumulative indices destroyed those siblings. All three implementations now follow the existing `NewLine._init_node` pattern: `elif not getattr(existing_node, "__webcompy_node__", False): existing_node.remove()`. Framework-managed nodes (created via `_init_new_node` or adopted) are never removed; prerendered-browser nodes (which are not marked `__webcompy_node__` until adopted) are still replaced on mismatch, preserving hydration semantics.

On the test side, `FakeDOMNode` now mirrors the browser marking: setting `__webcompy_prerendered_node__ = True` also clears `_webcompy_node` (browser prerendered children carry only the prerendered flag, per `_root_component._mark_as_prerendered`), so the mismatch-replacement branch of the guard is testable with fake DOM. A regression test pins `_init_node` replacing a prerendered node whose tag does not match.

### D6: `_re_index_children` starts from the container's own `_node_idx` for dynamic containers

`_re_index_children` previously always started at 0. That is correct for a plain `ElementWithChildren` (children live in its own node) but wrong for a `DynamicElement` (children live in the *parent's* node, so offsets are absolute). The dynamic-aware start (`self._node_idx if isinstance(self, DynamicElement) else 0`, via a lazy import) keeps the `DynamicElement._render`/`_hydrate_node` sibling re-index (materialization support) correct for nested dynamic containers instead of clobbering child indices with 0-based values.

### D7: `_reconcile_children` drops the trailing-node cleanup and keeps a full-render fallback

The old trailing cleanup (`while parent_node.childNodes.length > expected: childNodes[-1].remove()`) assumed the repeat's content extends to the end of the parent's childNodes; with following siblings it deleted them. Removed children are already cleaned up by `_remove_element`, so the cleanup is redundant. The merged single loop keeps an explicit `child._node_cache is None → await child._render()` fallback for reused children whose node cache was cleared (the original two-loop version rendered them; `_get_node()` alone would create an empty node without rendering the subtree).

### D8: `DynamicElement.__init__` initializes `_children` per instance

`RepeatElement`, `MarkdownForElement`, and the other `DynamicElement` subclasses did not assign `self._children` in `__init__`, so reads like the `_on_set_parent` guard (`if self._children:`) fell back to the shared `ElementWithChildren._children = []` class attribute. That is safe today (the class list is never mutated in place), but fragile: any future code path calling `_append_child` on an element before its instance list exists would pollute every dynamic container. `DynamicElement.__init__` now assigns `self._children = []` per instance, eliminating the shared-attribute reliance for the entire dynamic family.

### D9: `_re_index_children` falls back to 0 when `_node_idx` is unassigned

The D6 dynamic-aware start (`idx = self._node_idx`) is evaluated before the child loop, so calling `_re_index_children()` on a `DynamicElement` whose `_node_idx` was never assigned (e.g., parented via a path that does not set `_node_idx` first, such as `_create_child_element(parent, None, ...)` in repeat/switch/fragment generators or `_insert_child`) raised `AttributeError` — even for empty children. `RouterView._on_set_parent` calls `self._re_index_children()` directly and is the realistic caller. The start now uses `getattr(self, "_node_idx", 0)` so an unassigned dynamic container falls back to the previous 0-based behavior instead of crashing. Regression tests cover a parented `FragmentElement` without `_node_idx` and the `RouterView._on_set_parent` path.

### D10: `ElementAbstract._hydrate_node` adopts the D5 framework-node guard

The D5 guard (`elif not getattr(existing_node, "__webcompy_node__", False)`) was applied to the three `_init_node` implementations but `ElementAbstract._hydrate_node` kept the unconditional `if existing: existing.remove()` in its mismatch fallback. For consistency with D5, the hydration fallback now removes the existing node only when it is not framework-managed. Prerendered nodes (which carry only `__webcompy_prerendered_node__` and are never `__webcompy_node__`) are still removed on mismatch, preserving hydration replacement semantics; framework-managed nodes are preserved. This is defensive today (hydrate encounters framework nodes only on index collisions that the new re-index calls prevent) and aligns both code paths.

### D11: `MarkdownForElement._render` re-indexes siblings like `DynamicElement._render`

`DynamicElement._render` ends with `self._parent._re_index_children(False)` (sibling re-index for materialization support), but the `MarkdownForElement._render` override did not, making the two asymmetric. The override now calls it after `_position_element_nodes`. Harmless in the initial-render path (the parent's sequential loop reassigns following siblings anyway; `MarkdownForElement`'s `_node_count` is fixed after generation), but it makes hydration-time scheduled renders behave identically to other dynamic containers and keeps the sibling re-index invariant uniform across the dynamic family. Regression test: markdown-for initial render corrects a stale following-sibling `_node_idx`.

### D12: Refresh paths cancel stale hydration render tasks before replacing children

`DynamicElement._hydrate_node` schedules a render task for every unmounted child (children without adoptable prerendered DOM, e.g. in a client-only demo). The full-rebuild path of `RepeatElement._refresh` and the `_patch_children` paths of `SwitchElement._refresh`, `MarkdownForElement._refresh`, and `SuspenseElement._browser_resolve`/`_handle_error` replace those children, but the scheduled tasks stayed in the container's `_pending_render_tasks` — only the container's own `_remove_element` cancelled them. When the event loop later ran them, the removed children rendered and re-inserted their DOM nodes: the docs todo demo showed duplicated `<li>` nodes after the initial render, breaking `test_todo_remove_done_items` (e2e, prod and static). The fix extracts `DynamicElement._cancel_pending_render_tasks()` (from `_remove_element`) and calls it at the top of every refresh path that replaces children, so no render task scheduled for a replaced child can execute afterwards. `DynamicElement._render`/`_hydrate_node` are untouched: there the scheduled tasks are the intended render path (`self._hydrated` guards in-place rendering). Safe because the first refresh renders all children synchronously; later refreshes find the pending list empty (no-op).

## Risks / Trade-offs

- [Core rendering code touched in 7 files] → The change is provably behavior-preserving for single-node children (cumulative offset == enumerate index when all preceding siblings have `_node_count == 1`); multi-node children previously produced corrupted DOM, so no working behavior depends on current indexing. Full unit suite + full e2e suite (prod and static) as the safety net.
- [Refresh paths beyond the 12 index-assignment sites] → Review found the cumulative fix alone left refresh broken for (a) a reactive `{% if %}` inside a reactive `{% for %}` (orphaned switch batch leaking live callbacks, D4) and (b) layouts with a following sibling after the dynamic container (destructive `_init_node` takeover and a sibling-eating trailing cleanup in `_reconcile_children`, D5/D7). All are covered by new regression tests and e2e groups (`reactive-lists`, `dynamic-control`, `template`, `components`, `bootstrap-static`).
- [`_re_index_children` is 0-based by design for plain parents] → The dynamic-aware start (D6) keeps plain-parent semantics unchanged and makes the `DynamicElement` sibling re-index (materialization support) correct for nested dynamic parents.
- [Hidden fifth consumer of `_node_idx` assumes index-based values] → Audit `_node_idx` reads (`_position_element_nodes`, `_re_index_children`, `_children_length`, `_mount_node`) — all already consume cumulative offsets, so cumulative assignment aligns all producers with all consumers.
- [Plain containers use two coexisting base conventions] → `ElementWithChildren._render` bases children indices on `self._node_idx` while `_hydrate_node`/`_re_index_children`/`_append_child` are 0-based for plain parents. The `_render` convention is a pre-existing quirk (masked because initial renders append into empty parent nodes and the new re-index calls converge to 0-based after the first refresh) and is out of scope here; it is recorded as a future cleanup candidate rather than changed.

## Migration Plan

No migration. Behavior for currently-working cases is unchanged; previously-broken cases start rendering correctly. Rollback is a plain revert.

## Open Questions

None — the fix was validated end-to-end via monkey-patched reproductions before this design was written.
