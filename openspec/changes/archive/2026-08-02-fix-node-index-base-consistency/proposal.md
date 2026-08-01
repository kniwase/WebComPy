# Proposal: fix-node-index-base-consistency

## Why

`_node_idx` is defined as the offset of an element's first DOM node within the **nearest real-DOM-node ancestor's** `childNodes`. Under that definition the base for assigning children's `_node_idx` differs: regular (node-owning) elements reset to **base 0** (children live in the element's own node), while dynamic containers use **base `self._node_idx`** (children live in the parent's node at the container's offset). The codebase conflates these in two places:

- `ElementWithChildren._render` (`_base.py:38-39`) assigns regular elements' children with base `self._node_idx` (the element's own index in its parent), but `_re_index_children`/`_hydrate_node` use base 0 — contradicting each other. Most cases are later healed by `_re_index_children`, so the defect is latent, but the contradiction produces stale/inflated indices between render and the next re-index.
- `SwitchElement._refresh` (`_switch.py:112`) and `MarkdownForElement._refresh` call `self._parent._re_index_children(False)` with base 0. When the parent is a **dynamic** element (e.g., `RouterView._on_set_parent` sets `self._switch._parent = self`), this corrupts the switch's `_node_idx` to 0 regardless of the container's offset. Reproduced: a dynamic parent at index 1 containing a switch destroys its preceding sibling on the first toggle, and a `<div><header/><router-view/></div>` layout loses the header on the first navigation.

Found during a full audit of the template/element mechanism while scoping `fix-dynamic-child-node-index`.

## What Changes

- **B1**: Make `ElementWithChildren._render` assign children starting from base 0, matching `_re_index_children` and `_hydrate_node`. (Composes with `fix-dynamic-child-node-index`'s cumulative-offset loop: `idx = 0; for child: child._node_idx = idx; idx += child._node_count`.)
- **B2**: Stop `_re_index_children` from corrupting dynamic parents: re-index calls that reach dynamic parents (`SwitchElement._refresh`, `MarkdownForElement._refresh`) shall not reset a dynamic parent's children to base 0. Design chooses the concrete approach (e.g., a base-aware `_re_index_children` that starts from `self._node_idx` for dynamic elements, or call-site guards so refreshes re-index only regular parents).
- Audit all `_re_index_children` call sites and `RouterView._on_set_parent` for base correctness.
- Add regression tests: (a) an element at non-zero index containing a dynamic child followed by static siblings keeps correct order after refresh; (b) a `RouterView`-style dynamic parent (switch inside a dynamic container at non-zero offset) preserves preceding siblings across repeated toggles/navigation.

No public API changes.

## Capabilities

### New Capabilities

### Modified Capabilities

- `elements`: Add normative requirements pinning the `_node_idx` base rule — regular (node-owning) containers index children from 0, dynamic containers (no own node) index children from the container's own `_node_idx` — and that `_re_index_children` SHALL assign indices consistent with the parent's container kind, with regression scenarios for non-zero-offset containers.

## Known Issues Addressed

- **Base inconsistency in `_node_idx` assignment** (discovered during the `fix-dynamic-child-node-index` audit): `ElementWithChildren._render` uses `self._node_idx` base; `_re_index_children`/`_hydrate_node` use base 0; `_re_index_children` called on dynamic parents via switch/markdown refresh corrupts children to base 0.

## Non-goals

- Enumerate-vs-cumulative indexing (covered by `fix-dynamic-child-node-index`).
- `_init_node` sibling removal (covered by `fix-init-node-sibling-removal`).
- The reconciliation algorithm or hydration adoption semantics.
- Any public API change.

## Impact

- **Code**: `packages/webcompy/src/webcompy/elements/types/_base.py` (B1: base 0 in `_render`; possibly `_re_index_children` signature/behavior), `packages/webcompy/src/webcompy/elements/types/_switch.py`, `packages/webcompy/src/webcompy/template/_markdown_for.py` (B2: re-index call sites), and `packages/webcompy/src/webcompy/router/_view.py` (audit `_on_set_parent`).
- **Specs**: `openspec/specs/elements/spec.md` (delta: ADDED requirement(s) for base consistency).
- **Tests**: new regression tests in `tests/`; full unit suite and full e2e suite (incl. router groups) re-run.
- **Risk**: moderate. B1 changes child index values for non-first elements between render and re-index (currently inflated, now correct), which is strictly more correct; B2 touches routing refresh paths and must not regress existing router e2e (where `RouterView` is at offset 0). Careful ordering relative to `fix-dynamic-child-node-index` (both touch `_base.py:38-39`).