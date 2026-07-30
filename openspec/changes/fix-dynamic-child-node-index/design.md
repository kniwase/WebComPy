# Design: fix-dynamic-child-node-index

## Context

Element positioning in WebComPy relies on `_node_idx`: every `ElementAbstract` knows its start index within its parent's DOM `childNodes`. Dynamic containers (elements without their own DOM node — `DynamicElement` subclasses such as `RepeatElement`, `SwitchElement`, `FragmentElement`, `SuspenseElement`, `ClientOnlyElement`, plus the `_render` loop of `ElementBase`) assign children's `_node_idx` before rendering and rely on `_position_element_nodes` to insert/move DOM nodes at those indices.

The codebase already contains the correct cumulative-offset pattern in four places:

- `ElementWithChildren._re_index_children` (`_base.py:98-102`): `idx += child._node_count`
- `DynamicElement._hydrate_node` (`_dynamic.py:92-94`): `idx += child._node_count`
- `_position_element_nodes` (`_dynamic.py:206-210`): recursive cumulative walk
- `ElementWithChildren._append_child` (`_base.py:109`): last child's `node_idx + node_count`

However, 10 sites across 6 files assign `child._node_idx = self._node_idx + c_idx` (enumerate index). When every child has `_node_count == 1` (plain `Element`/`TextElement`), enumerate index equals cumulative offset, so the defect is invisible. When a child is a `FragmentElement` (multi-node — produced by template binding of multi-line bodies, since whitespace becomes `TextElement` siblings), subsequent children get indices that overlap earlier siblings' node ranges, and `insertBefore` positioning corrupts the DOM: earlier fragments' element nodes end up detached, leaving only the last fragment's elements.

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

## Decisions

### D1: Apply the existing cumulative pattern verbatim to all 10 sites

Each buggy loop becomes:

```python
idx = self._node_idx
for child in self._children:
    child._node_idx = idx
    idx += child._node_count
    ...  # existing per-child logic (render / position) unchanged
```

For `RepeatElement._reconcile_children` (`_repeat.py:204-205`), `node_offset + c_idx` becomes a running `node_offset += child._node_count` per iteration (children not reused still render afterward at their assigned index).

No helper extraction: the loop is 3 lines and the four existing correct sites already inline it; a shared helper can be introduced later if the pattern grows.

*Alternatives considered*: (a) Fixing only `RepeatElement` — rejected: `SwitchElement._render/_refresh`, `SuspenseElement`, `ClientOnlyElement._hydrate_node`, `ElementBase._render`, and `DynamicElement._render` share the identical defect and all accept fragment children (e.g., a switch branch whose generator returns multiple elements, a plain element containing a fragment child). (b) Changing `_position_element_nodes` to tolerate wrong indices — rejected: treats the symptom, leaves `_node_idx` semantics broken for reconciliation and `_children_length` arithmetic.

### D2: Regression tests via `TestRenderer` with multi-line templates

Multi-line template bodies are the minimal, realistic reproducer (whitespace text nodes force `FragmentElement` children). Tests assert the rendered `<li>`/`<p>` text sequences after initial render and after signal-driven refresh, following existing `TestRenderer` patterns from `tests/test_template_ssr.py`.

### D3: Fix is normative-pinned in the `elements` spec as an ADDED requirement

The existing requirements already describe the intended rendering behavior ("render all items", "display one branch"); this defect is an implementation violation, not a spec ambiguity. One ADDED requirement pins cumulative indexing explicitly so future container loops are reviewed against it.

## Risks / Trade-offs

- [Core rendering code touched in 6 files] → The change is provably behavior-preserving for single-node children (cumulative offset == enumerate index when all preceding siblings have `_node_count == 1`); multi-node children currently produce corrupted DOM, so no working behavior depends on current indexing. Full unit suite + full e2e suite (prod and static) as the safety net.
- [`_reconcile_children` running-offset variant diverges subtly] → Keep the existing per-child render decisions; only the index computation changes. Verify keyed e2e (`test_keyed_repeat`, `test_dict_repeat`) stays green.
- [Hidden fifth consumer of `_node_idx` assumes index-based values] → Audit `_node_idx` reads (`_position_element_nodes`, `_re_index_children`, `_children_length`, `_mount_node`) — all already consume cumulative offsets, so cumulative assignment aligns all producers with all consumers.

## Migration Plan

No migration. Behavior for currently-working cases is unchanged; previously-broken cases start rendering correctly. Rollback is a plain revert.

## Open Questions

None — the fix was validated end-to-end via monkey-patched reproductions before this design was written.
