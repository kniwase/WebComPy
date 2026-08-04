## Context

WebComPy hydrates prerendered DOM by **index-based adoption**. `ElementAbstract._get_existing_node()` returns `parent_node.childNodes[self._node_idx]`, and `ElementWithChildren._hydrate_node()` (`packages/webcompy/src/webcompy/elements/types/_base.py:47-57`) assigns each child a cumulative `_node_idx` from the sum of preceding siblings' `_node_count`:

```
Element tree children:   [ span,  TextEl("a"),  TextEl("b"),  span ]
_node_count:               1        1             1            1
assigned _node_idx:        0        1             2            3
```

This assumes the browser DOM has exactly matching `childNodes`. **It does not.** The HTML parser merges adjacent text nodes during parsing. An SSG-emitted fragment body like `<span></span>a` + `{{ x }}` (two interpolation holes that each become `#text`) is parsed into ONE `#text` node. The 7-node element tree becomes a 5-node browser DOM:

```
Element tree (7 nodes):  [ li,  span,  #text("a"), #text("b"),  span,  #text("c"),  li ]
Browser DOM after parse: [ li,  span,  #text("ab"),              span,  #text("c"),  li ]   ← 6 nodes
                            ^0    ^1     ^2                       ^3 merged into ^2
```

After the first merge point, every subsequent `_node_idx` resolves to the WRONG DOM node. `TextElement("b")` (idx 2) reads `childNodes[2]` which is now `#text("ab")`; `span` (idx 3) reads `childNodes[3]` which is `#text("c")`; and so on. Hydration adopts wrong nodes, reconcile leaves empty/stray nodes, and ordering breaks. This was reproduced during loop-metadata work and forced a single-element-body workaround in the e2e keyed-repeat page.

The bug only manifests under two conditions together: (1) a fragment/composite item body (multiple elements + adjacent text) and (2) keyed reconciliation that preserves DOM across updates. Static and unkeyed-list paths fully rebuild and self-heal.

## Goals / Non-Goals

**Goals:**

- Restore a 1:1 element-tree-to-DOM correspondence at hydration time by splitting parser-merged `#text` nodes, via a shared normalization helper used by BOTH `ElementWithChildren._hydrate_node` and `DynamicElement._hydrate_node`.
- Keep reconcile/positioning code untouched (it already assumes the 1:1 invariant; normalization restores it).
- Make the normalization unit-testable without a browser by adding `splitText` to the testing `FakeDOMNode`.
- Remove the e2e single-element-body workaround and guard the composite-body path with a regression test.

**Non-Goals:**

- Other parser normalizations (foster parenting, implicit tag closing, whitespace collapse in `<pre>`/`<textarea>`).
- Server `VirtualDOMNode` changes — the server never merges text.
- Redesigning index-based adoption (marker/comment anchoring) — Alternative A, rejected below.

## Decisions

### D1. Detect text runs at hydration time and split the merged DOM node (chosen — "Policy B")

Implement a shared helper (e.g. `_normalize_hydration_text_runs`) and call it from BOTH child-iteration loops: `ElementWithChildren._hydrate_node` (`_base.py`) AND `DynamicElement._hydrate_node` (`_dynamic.py`). The dynamic-container loop is NOT optional: `RepeatElement` items and `FragmentElement` bodies are hydrated through `DynamicElement._hydrate_node` (it overrides the base with its own `self._children` loop), and the fragment-level text runs — the whitespace/interpolation text inside composite loop bodies — live exactly there. Normalizing only the base-class loop would leave the actual bug site (keyed loops with composite bodies) broken.

The helper maintains a **live DOM cursor** alongside the element index (D6): runs are processed in element order at their current DOM position, and the DOM is re-read after each split. When the child at position `i` is a `TextElement` and a consecutive run of such children maps to a single merged `#text` node, split it (D6/D7), always splitting at every boundary including zero-length ones so trailing empty children receive their own nodes:

```
for each child in run (c_0 .. c_k):
    expected_text += c_j._get_text()
remainder = dom_text_node              # DOM #text node currently at the run start
for each child in run (c_0 .. c_k-1):
    remainder = remainder.splitText(utf16_len(c_j._get_text()))   # splitText truncates the
    remainder.__webcompy_prerendered_node__ = True                #   receiver to [0:offset]
advance DOM cursor past each split                                #   and returns the tail
```

`splitText(offset)` truncates the receiver to `[0:offset]` and returns a new sibling
`#text` node holding the tail, so each split must be issued on the returned remainder
node (chaining), never on the original node with cumulative offsets (the second call
would exceed the truncated length and raise `IndexSizeError` in the browser). The new
nodes are freshly created by the splitter and therefore lack the
`__webcompy_prerendered_node__` expando, so the helper marks them as prerendered to
keep `_hydrate_node`'s adoption path working. After splitting, each child once again maps to a distinct `childNodes[_node_idx]`, and the existing per-child `_hydrate_node()` / `_adopt_node()` proceeds unmodified. Reconcile, `_position_element_nodes`, and `_re_index_children` are NOT changed.

**Why split rather than re-index the element tree.** The element tree's `_node_count` is the source of truth used everywhere (render, refresh, reconcile, hydration, positioning). Re-indexing the tree to match the merged DOM would corrupt that invariant and ripple into every code path; splitting the DOM to match the tree is local, reversible, and confined to hydration.

**Idempotency.** A run is considered already normalized only when EVERY expected node (including empty ones) is present at its position with matching content — the old `content == first child` shortcut misclassified trailing empties and is gone. The common no-merge path is a fast per-node equality check.

### D2. Run boundaries — an element child terminates a run

A text run is a maximal consecutive sequence of `TextElement` children — the only element kind whose DOM contribution is a `#text` node, and therefore the only kind the parser can merge. Every other child (an `Element`, a component, a `NewLine` (`<br>`), or a `RawHTML` wrapper element) occupies its own non-mergeable DOM node and terminates a run. The detector keys off the expected DOM `nodeName` of each child (rather than the Python type alone), so it stays correct across all element kinds.

### D3. Content-mismatch fallback

If `dom_text_node.textContent != expected_text` (unexpected prerendered content, SSR/client divergence), the splitter does NOT split and instead falls back to the existing create/adopt behavior for that run. This avoids a misaligned split; the worst case is the pre-fix symptom for that one run, never worse. An assertion/log at `webcompy.logging.warning` flags the divergence for diagnosis without aborting hydration.

**Review correction (D8):** a mismatch also SHALL halt normalization for the remainder of the container. The original implementation recorded later runs up front and could split them at stale indices after an earlier run was skipped or split; the live-cursor rewrite makes such stale-index splitting impossible by stopping at the first mismatch and letting the pre-fix per-node create/adopt path handle the unreliable remainder.

### D4. Testing `FakeDOMNode.splitText`

`FakeDOMNode` (`packages/webcompy-testing/src/webcompy_testing/_dom.py`) extends the server `VirtualDOMNode`. Add a `splitText(offset)` method that creates a new `FakeDOMNode("#text", text_content=textContent[offset:])`, truncates the receiver to `textContent[:offset]`, inserts the new node into the parent's `childNodes` immediately after the receiver, and returns the new node — mirroring the standard DOM `Text.splitText` contract. **Review correction (D7):** `offset` SHALL be interpreted as UTF-16 code units (browser semantics), so the fake exercises the same astral-text boundaries the browser sees instead of masking them with code-point slicing.

### D5. Shared-Computed multi-consumer notification fix (discovered during implementation)

Building the composite-body regression guard (task 5) exposed a pre-existing signal-graph bug that is otherwise unreachable with single-element loop bodies. In a composite dict-loop body, `{{ loop.index }}` and `{{ loop.length }}` holes in different places (e.g. a text prefix and a span) resolve to the SAME `LoopMetadata` `Computed` instances, so one `Computed` can have multiple `CallbackConsumerNode` consumers. `CallbackConsumerNode._dispatch` captured `old_version = producer.version` at dispatch start and returned when `version <= old_version`. Within one mutation, the first consumer's `_dispatch` recomputed the producer (`producer_update_value_version` recomputes at most once per epoch); the second consumer's dispatch then found the producer already clean for the epoch, its version did not advance during the second dispatch, and the callback was silently dropped — the second consumer's DOM node stayed stale after dict rotation (observed: prefix holes updated, span's index/length did not).

Fix: `CallbackConsumerNode` tracks `_last_notified_value` (initialized from the producer's value at registration) and fires the callback whenever the recomputed value differs under the framework's `is`/`==` equality — independent of which consumer's dispatch recomputed the producer first. The subscription-time version bump (in `producer_add_live_consumer`) no longer pollutes the comparison because the check is value-based, not version-based. This is a `reactive` capability fix, distinct from the hydration normalization; it is included here because the composite-body regression guard cannot pass without it.

### D6. Live-DOM-cursor normalization (review correction)

The original helper collected `(dom_idx, run)` pairs against the pre-normalization `childNodes.length`, then split each recorded run. A later run whose logical position sat at or beyond the initial length was never recorded, and a run recorded before an earlier split could resolve to the wrong node after that split inserted nodes. The rewrite processes runs in a single pass over the element children with a DOM cursor, re-reading `parent_node.childNodes` after every mutation, so each run is always normalized at its true current position. Runs of a single non-empty child are skipped (nothing can be merged); runs of two or more children are normalized in place.

### D7. UTF-16 code-unit offsets (review correction)

`Text.splitText` takes an offset in UTF-16 code units; `len(str)` counts code points. For astral characters (e.g. `😀`) the code-point length under-counts, splitting inside a surrogate pair. A shared internal helper `_utf16_length(value)` (UTF-16LE surrogatepass byte length ÷ 2) computes the browser-correct offset, and `FakeDOMNode.splitText` interprets offsets the same way (splitting inside a surrogate pair yields lone-surrogate halves, matching the browser). A unit test asserts the split result and that adoption performs no text rewrite (the `textContent_write_count` stays zero) when the boundary is correct.

### D8. Empty-run materialization and mismatch halt (review correction)

Empty text children are real element-tree nodes, but the parser/SSG emits nothing for them. Two cases are handled:

- A run whose parts are all empty and whose DOM position has no `#text` node (the parser emitted nothing) is materialized: one empty prerendered `#text` node per child, inserted at the run's position via the DOM port. Without this, the first empty child would adopt (and remove) the following sibling node — the pre-fix breakage.
- A run whose DOM text content does not equal the concatenated expected text is a divergence: warn via `webcompy.logging.warning` and halt normalization for the remainder of the container. The pre-fix per-node create/adopt path then handles the remainder — the "never worse" guarantee.

### D9. Edge-aware notification snapshots (review correction)

`producer_notify_consumers` collected bare consumers up front and `_notify_before_callbacks` collected callback nodes up front. If a callback destroys another consumer mid-sweep, the destroyed consumer is still in the snapshot and would fire (after-update) or be notified (before-update) despite `consumer_destroy` having removed its edges — violating deterministic cleanup. The sweeps now snapshot `SignalEdge` objects, `_detach_consumer_edge` marks an edge inactive at detach time, and the mark/dispatch loop skips inactive edges. Detached consumers are never newly dispatched or scheduled; async callbacks already scheduled before destruction are not cancellable by this fix.

### D10. Dirty-Computed subscription baseline (review correction)

`CallbackConsumerNode.__init__` captured `producer._value` without bringing a dirty lazy `Computed` current, so a callback registered while the producer was dirty could false-fire on a later equal result or miss the return to the registration-time value. For `on_after_updating` on a `Computed`, `__init__` now runs `producer_update_value_version(producer)` (which recomputes the dirty producer without any active consumer, so no graph edges are created) and captures the current value as `_last_notified_value` BEFORE `producer_add_live_consumer` adds the edge. Ordinary `Signal` producers and before-update callbacks keep no baseline; `_last_notified_value` is only meaningful for after-update `Computed` callbacks.

### Alternative A (rejected) — Comment separators at SSG emit time

Emitting an HTML comment between every element-tree child so the browser parser preserves node boundaries. Rejected because EVERY index-based code path (`_init_node`, `_get_existing_node`, `_mount_node`, `_position_element_nodes`, reconcile) would have to become comment-aware (skip comment nodes in `childNodes` indexing), touching the entire element subsystem and the recently-stabilized index math (#218–#221). Scope explosion for a hydration-only problem.

### Alternative C (rejected) — Shared text-run node model

Modeling adjacent text children as a single shared DOM node with sub-runs, eliminating the merge by construction. Rejected as a redesign of the element tree's node-count model — same ripple risk as Alternative A, and incompatible with the existing `_node_count == 1` per-leaf invariant.

## Risks / Trade-offs

- [Boundary computation error mis-splits text] → Mitigated by content-equality guard (D3): split only when `dom.textContent == concat(expected)`, else warn and halt (D8). Task 1 (failing spike) locks the contract before implementation.
- [Performance on large lists] → Normalization is O(total text length) per hydrated container and runs once at hydration; reconcile/refresh are unaffected. Acceptable for typical list sizes.
- [Edge case: empty `TextElement` (`""`)] → Contributes zero-length text; zero-length boundaries are split, and all-empty runs with no DOM node are materialized as empty prerendered nodes (D8). Covered by unit tests.
- [`RawHTML` with nested elements] → `RawHTML` renders a wrapper element (default `<span>`), so it terminates a text run; its inner HTML is not part of sibling indexing. Covered by D2.
- [Browser `splitText` availability] → `Text.splitText` is a standard DOM API present in all target browsers (and now in `FakeDOMNode`); invoked through the existing DOM port node object, no new port needed.
- [Text normalizations other than merging (CRLF→LF, entity decoding) cause content mismatch] → The content-equality guard treats them as divergence: warn and fall back to the pre-fix create/adopt path for the remainder of the container. Text is still rendered correctly via adoption overwrite; only the 1:1 node structure is not restored for that container.

## Migration Plan

None required for application code. The e2e keyed-repeat page's single-element-body workaround is reverted to a composite body as part of this change (it becomes the regression guard). Any downstream app that relied on the pre-fix behavior (none known) would simply hydrate correctly.

## Open Questions

- Should the content-mismatch fallback (D3) be a hard error in development builds? Deferred — a warning is the safer default for the first landing; tightening to an error can follow if divergence proves rare in practice.
