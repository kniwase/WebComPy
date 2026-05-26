# Elements Delta

## ADDED Requirements

### Requirement: _mount_node() shall recover detached nodes when _mounted flag is True

`_mount_node()` SHALL handle four states based on the `_mounted` flag and the node's `parentNode`:

- `_mounted is None`: First-time mount — insert or append the node at `_node_idx`
- `_mounted is False`: Remount after `_detach_node()` — replace the remount placeholder
- `_mounted is True` AND `node.parentNode is not None`: Normal state — skip, node is already in the DOM
- `_mounted is True` AND `node.parentNode is None`: Detached recovery — the node was adopted (via `_adopt_node()`) but subsequently detached from the DOM by external code; SHALL reinsert the node at `_node_idx`

After mounting or remounting, `_mounted` SHALL be set to `True`.

#### Scenario: First-time mount
- **WHEN** `_mount_node()` is called with `_mounted is None`
- **AND** the parent DOM node exists
- **THEN** the node SHALL be inserted into the parent at `_node_idx`
- **AND** `_mounted` SHALL be set to `True`

#### Scenario: Remount after detach_node
- **WHEN** `_mount_node()` is called with `_mounted is False` and `_remount_to` is set
- **THEN** the node SHALL replace `_remount_to` in the parent
- **AND** `_remount_to` SHALL be cleared
- **AND** `_mounted` SHALL be set to `True`

#### Scenario: Skip when already mounted and in DOM
- **WHEN** `_mount_node()` is called with `_mounted is True` and `node.parentNode is not None`
- **THEN** no DOM operations SHALL be performed
- **AND** `_mounted` SHALL remain `True`

#### Scenario: Recover detached node after external DOM mutation
- **WHEN** `_mount_node()` is called with `_mounted is True` and `node.parentNode is None`
- **THEN** the node SHALL be reinserted into the parent at `_node_idx`
- **AND** the node SHALL be appended if `_node_idx` exceeds the parent's child list length
- **AND** `_mounted` SHALL remain `True`

#### Scenario: Detached node recovery does not affect DynamicElement
- **WHEN** a `DynamicElement` subclass has a detached node
- **THEN** the standard `_mount_node()` logic for `_mounted is True` SHALL not interfere with DynamicElement's own rendering path

### Requirement: NewLine._init_node() shall not remove WebComPy-managed DOM nodes

When `NewLine._init_node()` finds an existing DOM node at its expected sibling index and the node's tag does not match `<br>`, it SHALL check whether the node is managed by WebComPy (marked with `__webcompy_node__`). If the node has `__webcompy_node__` set, `_init_node()` SHALL NOT call `existing_node.remove()`, preserving the node for its owning element. This prevents `NewLine` from destroying adopted WebComPy-managed nodes during SPA navigation when `_patch_children()` shifts DOM siblings.

#### Scenario: NewLine preserves adopted WebComPy node during SPA navigation
- **WHEN** `_patch_children()` removes an unmatched old `<br>` node from the parent DOM
- **AND** subsequent sibling indices shift so `NewLine._init_node()` finds a `__webcompy_node__`-marked `<div>` instead of a `<br>`
- **THEN** `NewLine._init_node()` SHALL NOT call `existing_node.remove()`
- **AND** the adopted WebComPy-managed `<div>` SHALL remain in the DOM

#### Scenario: NewLine still removes non-WebComPy nodes
- **WHEN** `NewLine._init_node()` finds an existing DOM node without `__webcompy_node__` at its expected sibling index
- **AND** the node's tag does not match `<br>`
- **THEN** `existing_node.remove()` SHALL be called to clean up the unexpected node
