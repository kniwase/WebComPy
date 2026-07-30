# Delta: elements

## ADDED Requirements

### Requirement: Dynamic containers shall assign child node indices by cumulative node offset

When a container element assigns `_node_idx` to its children during render, refresh, reconciliation, or hydration, each child's index SHALL be the container's own `_node_idx` plus the sum of all preceding siblings' `_node_count` (cumulative node offset). Containers SHALL NOT use the child's enumerate position in the children list as the node offset. This applies to `ElementBase._render`, `DynamicElement._render`, `RepeatElement._refresh` (full-rebuild path), `RepeatElement._reconcile_children`, `SwitchElement._render`, `SwitchElement._refresh`, `SuspenseElement`, and `ClientOnlyElement`, matching the existing cumulative behavior of `_re_index_children`, `_hydrate_node`, `_position_element_nodes`, and `_append_child`. For children with `_node_count == 1` the two schemes coincide; multi-node children (`FragmentElement`) MUST be positioned at non-overlapping offsets.

#### Scenario: Multi-line template for-loop renders all items on initial render
- **WHEN** a template contains `{% for item in items %}` with a multi-line body (whitespace producing `TextElement` siblings, i.e., `FragmentElement` children) over a `ReactiveList`
- **THEN** the initial render SHALL produce one element per item in order, with no item's nodes lost or overlapped

#### Scenario: Multi-line template for-loop keeps all items after list mutation
- **WHEN** a reactive `{% for %}` with a multi-line body has rendered and the underlying `ReactiveList` is mutated (e.g., first item removed)
- **THEN** the refreshed DOM SHALL contain exactly the elements for the updated items in order

#### Scenario: Multi-element if branch toggles without losing nodes
- **WHEN** an `{% if %}` branch contains multiple sibling elements (wrapped in `FragmentElement`) and the condition signal toggles
- **THEN** the outgoing branch's nodes SHALL be removed and the incoming branch's elements SHALL all be present at correct positions

#### Scenario: Keyed reconciliation positions fragment children at non-overlapping offsets
- **WHEN** `repeat` with a `key` function (or `ReactiveDict`) renders templates that produce multi-node children and the collection is mutated
- **THEN** reused and newly created children SHALL be positioned by cumulative node offset with no overlapping `_node_idx` values
