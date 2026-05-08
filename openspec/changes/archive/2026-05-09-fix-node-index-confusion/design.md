## Context

`_patch_children()` is a module-level function in `_dynamic.py` used by `SwitchElement._refresh()` to reconcile old and new child elements after a condition change. It calls `_reposition_node(child, new_idx)` to move a DOM node to its correct place within the parent. However, `new_idx` is a local child index (0-based within the DynamicElement's children list), while `_reposition_node` uses it directly as an index into `parent_node.childNodes` — which is the global DOM child list.

```
Parent DOM node (e.g., <article>)
├── childNodes[0]: <h2> (static sibling)
├── childNodes[1]: <div> (old component, node_idx=1)
├── ...
```

When `SwitchElement._refresh()` calls `_patch_children([old_div], [new_div])`, the function calls `_reposition_node(new_div, 0)` — index 0 points to childNodes[0] (the `<h2>` sibling), not childNodes[1] where the component actually belongs. The correct global index is `SwitchElement._node_idx + new_idx = 1 + 0 = 1`.

The recursive `_patch_children` calls (lines 108, 122) on ElementBase descendants are unaffected because ElementBase has its own real DOM node, and children are repositioned within that node's own childNodes (where local = global).

## Goals / Non-Goals

**Goals:**
- Fix DOM order corruption when `_patch_children()` is called on a DynamicElement that has preceding sibling DOM nodes in its parent
- Ensure router transitions, switch case changes, and any other `_patch_children` invocation produce correct DOM order
- Minimal change with no API impact

**Non-Goals:**
- Add virtual DOM diffing
- Change the reconciliation algorithm itself
- Modify `RepeatElement` (its `_reconcile_children` already uses `node_offset = self._node_idx`)

## Decisions

### Approach: Add `node_idx_offset` parameter to `_patch_children()`

**Chosen:** Add an optional `node_idx_offset: int = 0` parameter to `_patch_children()`. At the two `_reposition_node` call sites, use `node_idx_offset + new_idx` instead of `new_idx`. The caller (`SwitchElement._refresh()`) passes `self._node_idx` as the offset.

**Alternatives considered:**

1. **Compute offset inside `_reposition_node` via parent chain traversal** — More complex and couples `_reposition_node` to element tree structure. Risk of infinite loops if parent chain is malformed.

2. **Inline the offset computation at call sites** — `_patch_children` doesn't know the DynamicElement's offset since it's a module-level function. Would require storing offset in a closure or module variable, which is fragile.

3. **Make `_patch_children` a method on DynamicElement** — Would require refactoring the recursive calls inside `_patch_children` (which operate on ElementBase, not DynamicElement). Unnecessary scope increase.

### Affected locations

Two `_reposition_node` call sites in `_patch_children()`:
- Line 109: position-match case → `_reposition_node(new_child, node_idx_offset + new_idx)`
- Line 123: scan-match case → `_reposition_node(new_child, node_idx_offset + new_idx)`

One caller:
- `SwitchElement._refresh()` line 70: `_patch_children(old_children, new_children, self._node_idx)`

## Risks / Trade-offs

- **Risk: Future callers forget the offset parameter** → Mitigation: The parameter has a default of `0` (backward compatible), and tests cover the sibling scenario. If a new DynamicElement subclass calls `_patch_children`, missing the offset would only cause issues when there are preceding siblings — which the existing e2e tests for nested dynamics would catch.
- **Risk: Recursive `_patch_children` calls might propagate offset incorrectly** → Mitigation: Recursive calls (lines 108, 122) already operate within an ElementBase's own childNodes where local=global. These calls will use the default `0` offset, which is correct.
