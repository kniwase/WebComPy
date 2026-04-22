# Elements — Delta: feat-hydration-full

## Changes

### Added: _adopt_node() and _hydrate_node() for full hydration

When full hydration is enabled, elements SHALL use `_hydrate_node()` instead of `_init_node()` for prerendered nodes. `_hydrate_node()` checks for an existing prerendered node and delegates to `_adopt_node()` if found, or falls back to `_init_node()` if not.

`ElementBase._adopt_node(node)` SHALL adopt an existing DOM node by:
- Setting `_node_cache` and `_mounted=True`
- Setting `node.__webcompy_node__ = True`
- Removing stale attributes (present on node but not in current attrs)
- Setting matching attributes with equality check
- Registering Signal callbacks for reactive attributes
- Attaching event handlers
- Initializing `DomNodeRef` if present
- NOT calling `_mount_node()` (the node is already in the DOM)

`TextElement._adopt_node(node)` SHALL adopt an existing text node by:
- Setting `_node_cache` and `_mounted=True`
- Conditionally updating `textContent` if it differs

`ElementAbstract._hydrate_node()` SHALL check for a prerendered node and call `_adopt_node()` if found, otherwise fall back to `_init_node()`.