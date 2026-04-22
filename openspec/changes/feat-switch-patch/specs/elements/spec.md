# Elements — Delta: feat-switch-patch

## ADDED Requirements

### Requirement: ElementBase._adopt_node() shall adopt an existing DOM node
`ElementBase._adopt_node(node)` SHALL adopt an existing DOM node by setting `_node_cache`, `_mounted=True`, applying attribute diff, registering Signal callbacks, attaching event handlers, and initializing `DomNodeRef` — without calling `_mount_node()` or any DOM creation API.

#### Scenario: Adopting a prerendered element
- **WHEN** `_adopt_node(node)` is called on an existing DOM node
- **THEN** the element SHALL set `_node_cache` and `_mounted=True`
- **AND** attribute diff, Signal callbacks, event handlers, and DomNodeRef SHALL be initialized
- **AND** `_mount_node()` and DOM creation APIs SHALL NOT be called

### Requirement: TextElement._adopt_node() shall adopt an existing text node
`TextElement._adopt_node(node)` SHALL adopt an existing text node by setting `_node_cache`, `_mounted=True`, and conditionally updating `textContent` if it differs.

#### Scenario: Adopting a text node with matching content
- **WHEN** `_adopt_node(node)` is called and the node's `textContent` matches the element's value
- **THEN** the text node SHALL be adopted without updating `textContent`

#### Scenario: Adopting a text node with differing content
- **WHEN** `_adopt_node(node)` is called and the node's `textContent` differs from the element's value
- **THEN** `textContent` SHALL be updated to match the element's current value

### Requirement: ElementBase._detach_from_node() shall release Python-side resources
`ElementBase._detach_from_node()` SHALL release Python-side resources (event handler proxies via `destroy()`, Signal callbacks, DomNodeRef) without removing the DOM node. It SHALL be called when an old element's DOM node is adopted by a new element.

#### Scenario: Detaching from an adopted DOM node
- **WHEN** an old element's DOM node is adopted by a new element during patching
- **THEN** `_detach_from_node()` SHALL destroy event handler proxies, remove Signal callbacks, and clear DomNodeRef
- **AND** the DOM node itself SHALL NOT be removed from the document

### Requirement: _patch_children() and _is_patchable() shall support node reuse across conditional branches
`_patch_children(old_children, new_children)` SHALL recursively compare old and new element lists by tag name, adopting matching DOM nodes and cleaning up unmatched old elements. Matched old elements are detached via `_detach_from_node()`; unmatched old elements are removed via `_remove_element()`.

`_is_patchable(old, new)` SHALL return `True` when two elements share the same tag name (for `ElementBase`) or are both `TextElement` instances. `DynamicElement` pairs are never patchable. `Component` pairs are patchable when their root tag names match (with a rollback path to exclude Components).

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

## MODIFIED Requirements

### Requirement: Conditional rendering shall reuse DOM nodes when branches share structure
When a conditional branch changes, `SwitchElement._refresh()` SHALL use `_patch_children()` to compare old and new children, adopting matching DOM nodes instead of destroying and recreating all children. Only unadopted new children SHALL call `_render()`. The deferred rendering mechanism (`start_defer_after_rendering` / `end_defer_after_rendering`) SHALL be preserved.

#### Scenario: Switching between branches with shared structure
- **WHEN** a `SwitchElement` condition changes from one branch to another
- **AND** the old and new branches share tag names at the same positions
- **THEN** matching DOM nodes SHALL be adopted rather than destroyed and recreated
- **AND** the deferred rendering mechanism SHALL be preserved

#### Scenario: Switching between branches with different structure
- **WHEN** a `SwitchElement` condition changes to a branch with entirely different structure
- **THEN** old elements SHALL be removed via `_remove_element()` and new elements SHALL be created via `_render()`