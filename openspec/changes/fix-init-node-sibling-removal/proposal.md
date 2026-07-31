# Proposal: fix-init-node-sibling-removal

## Why

`ElementBase._init_node`, `TextElement._init_node`, and `RawHTMLElement._init_node` unconditionally `remove()` whatever DOM node `_get_existing_node()` finds at the element's `_node_idx` when that node is not an adoptable prerendered node. The underlying assumption — "the node at my index is a stale copy of myself" — holds only during prerender adoption, not when freshly created elements render into an already-populated live DOM. When a dynamic container refresh renders new children at indices occupied by following siblings, those innocent siblings are permanently destroyed. Reproduced on current code (all with perfectly correct `_node_idx` values):

- `<div><p>A</p>{% for i in items %}<li>{{ i }}</li>{% endfor %}<p>B</p></div>` — after `items.append(...)`, `<p>B</p>` is gone from the DOM
- `{% if %}` branch toggle (non-patchable tags) with a trailing sibling — sibling lost
- Keyed/dict `repeat` item insertion with a trailing sibling — sibling lost

Found during a full audit of the template/element mechanism while scoping `fix-dynamic-child-node-index`.

## What Changes

- Align the removal guard in `ElementBase._init_node` (`elements/types/_element.py`), `TextElement._init_node`, and `RawHTMLElement._init_node` (`elements/types/_text.py`) with the guard `NewLine._init_node` already has: only remove the existing node when it is NOT a webcompy-managed node (`not getattr(existing_node, "__webcompy_node__", False)`).
- Prerendered nodes never carry `__webcompy_node__` (only `__webcompy_prerendered_node__`, set by `_mark_as_prerendered`), so the hydration adoption path (tag-mismatched prerendered node removed and recreated) is preserved unchanged.
- Add regression tests pinning that following siblings survive: unkeyed `{% for %}` refresh (append/pop), keyed/dict repeat insertion, and `{% if %}` branch toggle with non-patchable branch tags.

No public API changes.

## Capabilities

### New Capabilities

### Modified Capabilities

- `elements`: Add a normative requirement that fresh node initialization must never remove a webcompy-managed DOM node found at the target index, with regression scenarios for dynamic-container refreshes followed by static siblings.

## Known Issues Addressed

- **Dynamic container refresh destroys following static siblings** (discovered during the `fix-dynamic-child-node-index` audit): any repeat/switch refresh that creates fresh elements at indices occupied by later siblings removes those siblings from the DOM permanently.

## Non-goals

- `_node_idx` computation itself (enumerate-vs-cumulative is `fix-dynamic-child-node-index`; base-consistency is `fix-node-index-base-consistency`).
- Changes to `_patch_children` / `_reposition_node` / the reconciliation algorithm.
- Changes to the hydration/prerender adoption semantics (tag-mismatch prerendered nodes must still be removed and recreated).
- `NewLine._init_node` (already has the protective guard).

## Impact

- **Code**: `packages/webcompy/src/webcompy/elements/types/_element.py` (1 site), `packages/webcompy/src/webcompy/elements/types/_text.py` (2 sites) — one-condition guard additions only.
- **Specs**: `openspec/specs/elements/spec.md` (delta: one ADDED requirement).
- **Tests**: new regression tests in `tests/` (TestRenderer-based); full unit suite and full e2e suite re-run.
- **Risk**: low-to-moderate. The failure mode flips from "innocent node deleted" to "stale managed node may be left behind" (safe direction). Legitimate stale-managed-node removal paths (remount flows) must be audited: `_mount_node` handles remount via `_remount_to`/`replaceChild` and `_detach_from_node` clears `_node_cache`, so `_init_node` is not on those paths. Prerender mismatch removal is preserved because prerendered nodes lack `__webcompy_node__`.
