## Why

Hydration adopts prerendered DOM nodes by sibling index: `_get_existing_node()` returns `parent_node.childNodes[_node_idx]`, and `ElementWithChildren._hydrate_node` assigns each child a cumulative `_node_idx` from the element tree's `_node_count` sum. This assumes a 1:1 correspondence between element-tree nodes and browser DOM nodes. But the HTML parser **merges adjacent text nodes** during parsing, so the browser DOM ends up with fewer `#text` nodes than the element tree expects. In keyed loops whose item body is a fragment (multiple elements interleaved with whitespace/interpolation text), the indices drift after the first merge point, and hydration adopts the wrong nodes — producing empty nodes, leftover prerendered nodes, and broken ordering after reconcile. This was observed concretely: an element tree of 7 nodes renders a browser DOM of 5 nodes after parsing.

## What Changes

- Add a shared hydration-time text-run normalization helper (in `packages/webcompy/src/webcompy/elements/types/_base.py`) and invoke it from BOTH `ElementWithChildren._hydrate_node` AND `DynamicElement._hydrate_node` (`packages/webcompy/src/webcompy/elements/types/_dynamic.py`): when iterating children to assign `_node_idx`, detect consecutive `TextElement` runs whose corresponding DOM `#text` was merged by the parser (`NewLine`/`RawHTML` render element nodes and terminate runs), and call `splitText` on the merged DOM text node at the cumulative expected-text boundary so the 1:1 index correspondence is restored before per-child adoption proceeds. Reconcile and positioning logic is unchanged.
- Fix a pre-existing signal-graph bug exposed by the composite-body regression guard: a `Computed` with multiple `on_after_updating` consumers only notified the FIRST consumer per mutation — the remaining consumers were silently dropped when their dispatch ran after the Computed had already been recomputed within the same epoch, leaving their DOM nodes stale. `CallbackConsumerNode` now tracks its last-notified value and fires whenever the recomputed value differs (`packages/webcompy/src/webcompy/signal/_base.py`).
- Add `splitText` support to the testing `FakeDOMNode` (`packages/webcompy-testing/src/webcompy_testing/_dom.py`) so the normalization path is unit-testable browserlessly.
- Add unit tests covering: fragment body (element + adjacent text) hydration with merged DOM text; keyed `ReactiveDict` loop with composite item body hydrating and reconciling correctly; edge cases (empty text, `NewLine`, `RawHTML`, content mismatch); shared-Computed multi-consumer notification.
- Restore the e2e dict loop in `e2e/core/my_app/pages/template_control_flow.py` to a composite body (the single-element-body workaround added to dodge this bug) as a regression guard, plus a dedicated hydration parity check.
- Non-goal: no `VirtualDOMNode` (server) changes — the server never merges text nodes; normalization is a browser-hydration concern only.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `elements`: adds a requirement that hydration SHALL normalize parser-merged text nodes to element-tree granularity before index-based adoption, formalizing the contract that `_hydrate_node` must not assume a pristine 1:1 DOM when adjacent text nodes are present.
- `signal`: adds a requirement that a `Computed` SHALL notify every callback consumer whose last-notified value differs after a recompute, fixing the multi-consumer dispatch drop (exposed by the composite-body regression guard).

## Impact

- **Affected code**: `packages/webcompy/src/webcompy/elements/types/_base.py` (shared normalization helper + `ElementWithChildren._hydrate_node`); `packages/webcompy/src/webcompy/elements/types/_dynamic.py` (`DynamicElement._hydrate_node` call site); `packages/webcompy/src/webcompy/signal/_base.py` (`CallbackConsumerNode` last-notified-value tracking); `packages/webcompy-testing/src/webcompy_testing/_dom.py` (`FakeDOMNode.splitText`).
- **Tests**: new unit tests (hydration with merged text); `tests/test_full_hydration.py` / a new `tests/test_hydration_text_merge.py`; shared-Computed multi-consumer tests in `tests/test_signal.py`; e2e dict-loop composite-body restoration in `e2e/core/my_app/pages/template_control_flow.py` and parity fixture extension in `e2e/core/my_app/parity_fixtures.py`.
- **APIs/dependencies**: none public. `splitText` is invoked on the existing DOM port node object (a standard `Text.splitText` API already available in the browser).
- **Risk**: moderate. The normalization runs only during hydration when a text-run mismatch is detected; the no-merge common path is untouched. Incorrect boundary computation could mis-split text, mitigated by content-equality assertions and the spike test (task 1).

## Known Issues Addressed

Addresses the hydration text-node drift that forced a single-element-body workaround in the e2e dict loop (`e2e/core/my_app/pages/template_control_flow.py`) during the `feat-loop-metadata` work. Also supersedes the stale known-issue note *"TextElement does not hydrate pre-rendered text nodes (always creates new text node)"* in `openspec/config.yaml` — `TextElement._adopt_node` already exists; this change ensures those adopted text nodes align with the correct sibling index under parser merging.

Additionally fixes a pre-existing signal-graph bug discovered while building the composite-body regression guard: `CallbackConsumerNode._dispatch` dropped the 2nd+ consumer of a shared `Computed` within one mutation epoch (the first consumer's dispatch recomputed the Computed; later consumers saw an unchanged version and were skipped), leaving DOM nodes stale after dict rotation. The bug is only reachable when one `Computed` (e.g. template `loop.index`/`loop.length` metadata) feeds multiple holes in the same body — exactly the composite-body case this change guards.

## Non-goals

- Other HTML parser normalizations beyond adjacent-text merging: table foster parenting, implicit tag auto-closing, `<p>` auto-closing, comment handling, whitespace collapsing inside `<pre>`/`<textarea>`. These are documented separately and remain out of scope.
- Changes to the server-side `VirtualDOMNode` or the SSG HTML emitter — the server emits the element tree faithfully; merging is strictly a browser parse-time behavior.
- Redesigning the index-based adoption model itself (e.g., switching to marker/comment-based node anchoring) — that is a larger change rejected in the design (Alternative A).
- Changing reconcile/positioning code — normalization restores the 1:1 invariant those paths already assume.
