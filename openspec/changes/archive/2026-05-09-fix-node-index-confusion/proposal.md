## Why

When a `DynamicElement` (SwitchElement, RepeatElement, or RouterView) has sibling DOM nodes before it in the parent, patching children via `_patch_children()` corrupts the DOM order. The `_reposition_node()` function is called with a local child index (e.g. 0 for the first child) but uses it directly as a DOM index against `parent_node.childNodes`, ignoring the DynamicElement's own `_node_idx` offset. This causes elements to be inserted at wrong positions and sibling nodes to shift unexpectedly.

## What Changes

- Fix `_reposition_node` call sites inside `_patch_children()` to account for the DynamicElement's `_node_idx` offset when computing the target DOM position
- Update the internal `_patch_children()` signature to accept an optional `node_idx_offset` parameter, or alternatively compute the correct global index within `_reposition_node` by walking up to find the nearest static ancestor's offset
- No API changes, no breaking changes

## Capabilities

### New Capabilities

None. This is a bug fix.

### Modified Capabilities

- **elements**: `_patch_children()` and related internal functions SHALL compute the correct global DOM index when repositioning nodes, accounting for the DynamicElement's node index offset within its parent

## Impact

- `webcompy/elements/types/_dynamic.py` (`_patch_children`, `_reposition_node`)
- Affected user-visible scenarios: RouterView page transitions, SwitchElement case switching, RepeatElement reconciliation — all when the DynamicElement has preceding sibling DOM nodes in its parent
