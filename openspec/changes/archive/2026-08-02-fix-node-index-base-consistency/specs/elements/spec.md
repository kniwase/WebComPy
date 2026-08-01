# Delta: elements

## ADDED Requirements

### Requirement: Index assignment base SHALL match the container's node ownership

Assigning a child's `_node_idx` SHALL use a base determined by the container's relationship to the DOM: regular (node-owning) containers SHALL index their children from `0` (children occupy the container's own DOM node), and dynamic containers (no own DOM node) SHALL index their children from the container's own `_node_idx` (children occupy the nearest real-DOM-node ancestor's `childNodes`). This applies to `ElementWithChildren._render`, `ElementWithChildren._re_index_children`, and all dynamic-container render/refresh/hydration loops, and SHALL hold across initial render, refresh, keyed reconciliation, and hydration. Consistent with `DynamicElement._hydrate_node` (dynamic: base `self._node_idx`) and `ElementWithChildren._re_index_children`/`_hydrate_node` (regular: base `0`) for their respective kinds.

#### Scenario: Non-zero-offset regular element preserves trailing siblings after refresh
- **WHEN** a regular element whose own `_node_idx` is non-zero contains a dynamic child (e.g., `{% for %}`) followed by static siblings, and the iterable is mutated
- **THEN** the refreshed DOM SHALL keep the static siblings in their original order relative to the dynamic child's nodes

#### Scenario: Dynamic container at non-zero offset repositions children within its parent's node
- **WHEN** a dynamic container whose own `_node_idx` is `k > 0` re-renders or refreshes its children
- **THEN** each child's `_node_idx` SHALL equal `k` plus the cumulative node offset of preceding siblings within the container, and the child's DOM node SHALL be inserted at that index within the nearest real-DOM-node ancestor

### Requirement: `_re_index_children` SHALL be consistent with the receiver's container kind

The `_re_index_children` operation SHALL assign child indices using the same base rule as the container kind of the receiver: base `0` for `ElementWithChildren` (regular) and base `self._node_idx` for `DynamicElement` (dynamic). A refresh path that re-indexes a dynamic parent (e.g., `SwitchElement._refresh`, `MarkdownForElement._refresh`, `RouterView._on_set_parent`) SHALL NOT reset that parent's children to base `0` when the parent sits at a non-zero offset.

#### Scenario: RouterView-style dynamic parent preserves preceding siblings across toggles
- **WHEN** a dynamic parent at a non-zero offset contains a `SwitchElement` (the `RouterView` pattern) and the switch's condition is toggled repeatedly
- **THEN** the DOM nodes of the preceding siblings SHALL remain present and in order after each toggle, and the switch's branch content SHALL be positioned after them

#### Scenario: Re-indexing a dynamic parent at offset 0 is unchanged
- **WHEN** a dynamic container sits at `_node_idx == 0` (e.g., `RouterView` as the sole child of its parent) and `_re_index_children` runs after a refresh or as part of `RouterView._on_set_parent`
- **THEN** the assigned child indices SHALL equal the values produced under base `0` (preserving current behavior for the common case)