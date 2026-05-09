## Context

`_reposition_node()` at `_dynamic.py:74` receives an element and a target index, then moves the element's cached DOM node within its parent's `childNodes` list:

```python
def _reposition_node(element, new_index):
    node = element._node_cache
    parent = node.parentNode if node else None
    if not parent:
        return   # <-- early exit when node is detached
    if new_index < parent.childNodes.length:
        parent.insertBefore(node, parent.childNodes[new_index])
    else:
        parent.appendChild(node)
```

This early exit (`if not parent: return`) assumes `parentNode` is always non-null after initial mount. However, external code can detach nodes from the DOM (e.g., `hljs.highlightElement` replaces `innerHTML`, removing all child text nodes). When `_patch_children` adopts a detached text node and calls `_reposition_node`, the node's `parentNode` is `null`, and the function silently returns without reinserting.

The element tree (`element._parent`) already tracks the correct parent element. `element._parent._get_node()` returns the DOM node where the child should live.

## Goals / Non-Goals

**Goals:**
- Recover from externally-detached DOM nodes during `_reposition_node`
- Reinsert adopted nodes into the correct DOM parent at the correct index
- Single-point fix with no changes to other functions

**Non-Goals:**
- Prevent external code from modifying the DOM
- Detect or revert external DOM mutations proactively
- Handle cases where the parent element itself has been removed

## Decisions

### Approach: Resolve parent from element tree when DOM parent is null

**Chosen:** When `parent` is `null` (or `node` is `null`), resolve `parent` from `element._parent._get_node()` instead of from `node.parentNode`. The rest of the logic (insert at index) remains unchanged.

```python
def _reposition_node(element, new_index):
    node = element._node_cache
    parent = node.parentNode if node else None
    if not parent:
        parent = element._parent._get_node() if not isinstance(element, DynamicElement) else None
    if not parent:
        return
    ...
```

The `isinstance(element, DynamicElement)` guard is necessary because `DynamicElement._parent._get_node()` delegates to the DynamicElement's own parent (which could also be a DynamicElement), and DynamicElements have no DOM node of their own. In practice, `_reposition_node` is never called on a `DynamicElement` itself (they are not patchable), so this is a safety guard.

**Alternatives considered:**

1. **Check `node.parentNode` in `_mount_node` instead** — `_mount_node` already skips when `_mounted=True`. Changing this would break the existing lifecycle contract and could cause double-mounting in normal cases.

2. **Clear `_mounted` in `_adopt_node` when parent is null** — Would force `_mount_node` to run, but `_mount_node` uses `_node_idx` which may be stale. Too invasive.

3. **Disable patching when external mutations are detected** — Requires detecting mutations (expensive/not possible reliably). Forces full rebuild on every transition, losing the performance benefit of patching.

## Risks / Trade-offs

- **Risk: `element._parent._get_node()` returns a stale or wrong parent** → Mitigation: This is the same parent reference tracked throughout the VDOM tree that was used during initial mount. It only becomes invalid if the entire parent hierarchy has been removed from DOM, which `_remove_element` already handles.
- **Risk: Node is inserted but the surrounding DOM structure is inconsistent with VDOM expectations** → Mitigation: `ElementWithChildren._render` already runs cleanup (`remove` extra nodes) after children render. The cleanup logic uses `_children_length` which is based on VDOM, not the actual DOM state, and will remove excess nodes correctly.
