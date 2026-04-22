# Elements — Delta: feat-hydration-full

## MODIFIED Requirements

### Requirement: Pre-rendered DOM nodes shall be reused during hydration via adopt-and-hydrate
When full hydration is enabled, elements SHALL use `_hydrate_node()` instead of `_init_node()` for prerendered nodes. `_hydrate_node()` SHALL check for an existing prerendered node and delegate to `_adopt_node()` if found, or fall back to `_init_node()` if not.

#### Scenario: Hydrating an existing prerendered element
- **WHEN** `_hydrate_node()` is called and a prerendered node with matching tag exists
- **THEN** `_adopt_node(node)` SHALL be called to adopt the existing DOM node
- **AND** the framework SHALL NOT call `_mount_node()` since the node is already in the DOM

#### Scenario: No prerendered node available during hydration
- **WHEN** `_hydrate_node()` is called and no prerendered node exists
- **THEN** the element SHALL fall back to `_init_node()` for normal DOM creation and mounting

## ADDED Requirements

### Requirement: ElementBase._adopt_node() shall adopt an existing DOM node
`ElementBase._adopt_node(node)` SHALL adopt an existing DOM node by setting `_node_cache` and `_mounted=True`, setting `node.__webcompy_node__ = True`, removing stale attributes (present on node but not in current attrs), setting matching attributes with equality check, registering Signal callbacks for reactive attributes, attaching event handlers, and initializing `DomNodeRef` if present. It SHALL NOT call `_mount_node()`.

#### Scenario: Adopting a prerendered div element
- **WHEN** `_adopt_node(node)` is called on an existing `<div>` DOM node
- **THEN** the element SHALL set `_node_cache` and `_mounted=True`
- **AND** stale attributes SHALL be removed and matching attributes SHALL be set
- **AND** Signal callbacks and event handlers SHALL be registered
- **AND** `_mount_node()` SHALL NOT be called

### Requirement: TextElement._adopt_node() shall adopt an existing text node
`TextElement._adopt_node(node)` SHALL adopt an existing text node by setting `_node_cache` and `_mounted=True`, and conditionally updating `textContent` if it differs.

#### Scenario: Adopting a prerendered text node with matching content
- **WHEN** `_adopt_node(node)` is called on an existing `#text` node with matching content
- **THEN** the text node SHALL be adopted without updating `textContent`
- **AND** `_node_cache` and `_mounted=True` SHALL be set

#### Scenario: Adopting a prerendered text node with differing content
- **WHEN** `_adopt_node(node)` is called on an existing `#text` node with different content
- **THEN** `textContent` SHALL be updated to the element's current value
- **AND** `_node_cache` and `_mounted=True` SHALL be set