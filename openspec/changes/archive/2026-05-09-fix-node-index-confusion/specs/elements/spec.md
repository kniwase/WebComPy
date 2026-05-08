## MODIFIED Requirements

### Requirement: _patch_children() and _is_patchable() shall support node reuse across conditional branches
`_patch_children(old_children, new_children)` SHALL recursively compare old and new element lists by tag name, adopting matching DOM nodes and cleaning up unmatched old elements. Matched old elements are detached via `_detach_from_node()`; unmatched old elements are removed via `_remove_element()`. When repositioning nodes within the parent DOM, the DynamicElement's `_node_idx` SHALL be added as an offset so that children are placed at the correct global DOM position (accounting for any preceding sibling DOM nodes).

`_is_patchable(old, new)` SHALL return `True` when two elements share the same tag name (for `ElementBase`) or are both `TextElement` instances. `DynamicElement` pairs are never patchable. `Component` pairs are patchable when their root tag names match.

#### Scenario: Patching children with matching tag names
- **WHEN** `_patch_children()` compares old and new children with matching tag names
- **THEN** matching old elements SHALL be detached via `_detach_from_node()` and their nodes adopted by new elements
- **AND** only unadopted new children SHALL call `_render()`

#### Scenario: Patching children with unmatched elements
- **WHEN** `_patch_children()` finds old elements with no matching new element
- **THEN** unmatched old elements SHALL be removed via `_remove_element()`

#### Scenario: Checking patchability of two elements
- **WHEN** `_is_patchable(old, new)` is called on two `ElementBase` instances with the same tag name
- **THEN** it SHALL return `True`
- **WHEN** `_is_patchable(old, new)` is called on a `DynamicElement` pair
- **THEN** it SHALL return `False`

#### Scenario: Repositioning children when DynamicElement has preceding siblings
- **WHEN** `_patch_children()` is called on a DynamicElement whose `_node_idx` is greater than 0 (i.e., there are sibling DOM nodes before the DynamicElement's content in the parent)
- **AND** a child element is repositioned via `_reposition_node()`
- **THEN** the child SHALL be placed at `DynamicElement._node_idx + local_child_index` in the parent DOM
- **AND** preceding sibling DOM nodes SHALL remain at their original positions
