## ADDED Requirements

### Requirement: _reposition_node() shall recover detached DOM nodes
When `_reposition_node()` is called on an element whose cached DOM node has been detached from its DOM parent by an external mutation (i.e., `element._node_cache.parentNode` is `null`), the function SHALL resolve the correct parent DOM node from the element tree via `element._parent._get_node()` and reinsert the node at the target index. If `element._parent._get_node()` also fails to return a valid parent, the function SHALL return without error (no-op).

This requirement SHALL NOT apply to `DynamicElement` instances themselves (which have no DOM node of their own).

#### Scenario: Repositioning a text node detached by external code
- **WHEN** a `TextElement`'s cached DOM node has been removed from the DOM by external JavaScript (e.g., highlight.js replacing `innerHTML`)
- **AND** `_reposition_node()` is called on that `TextElement`
- **THEN** the text node SHALL be reinserted into the DOM at the correct position using the parent DOM node obtained from `element._parent._get_node()`
- **AND** if the target index exceeds the parent's child list length, the node SHALL be appended to the end

#### Scenario: Repositioning a node that is already in the DOM
- **WHEN** `_reposition_node()` is called on an element whose cached DOM node still has a valid `parentNode`
- **THEN** the function SHALL use the existing `parentNode` directly (preserving existing behavior)
