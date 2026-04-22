# Elements — Delta: feat-switch-patch

## Changes

### Added: _adopt_node() on ElementBase and TextElement

`ElementBase._adopt_node(node)` SHALL adopt an existing DOM node by setting `_node_cache`, `_mounted=True`, applying attribute diff, registering Signal callbacks, attaching event handlers, and initializing DomNodeRef — without calling `_mount_node()` or any DOM creation API.

`TextElement._adopt_node(node)` SHALL adopt an existing text node by setting `_node_cache`, `_mounted=True`, and conditionally updating `textContent` if it differs.

### Added: _detach_from_node() on ElementBase

`ElementBase._detach_from_node()` SHALL release Python-side resources (event handler proxies via `destroy()`, Signal callbacks, DomNodeRef) without removing the DOM node. Called when an old element's DOM node is adopted by a new element.

### Added: _patch_children() and _is_patchable()

`_patch_children(old_children, new_children)` SHALL recursively compare old and new element lists by tag name, adopting matching DOM nodes and cleaning up unmatched old elements. Matched old elements are detached via `_detach_from_node()`; unmatched old elements are removed via `_remove_element()`.

`_is_patchable(old, new)` SHALL return True when two elements share the same tag name (for ElementBase) or are both TextElement instances. DynamicElement pairs are never patchable. Component pairs are patchable when their root tag names match (with a rollback path to exclude Components).

### Updated: SwitchElement._refresh() uses _patch_children()

When a conditional branch changes, `SwitchElement._refresh()` SHALL use `_patch_children()` to compare old and new children, adopting matching DOM nodes instead of destroying and recreating all children. Only unadopted new children SHALL call `_render()`. The deferred rendering mechanism (start_defer_after_rendering / end_defer_after_rendering) SHALL be preserved.