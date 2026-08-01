# Delta: elements

## ADDED Requirements

### Requirement: Fresh node initialization shall not remove webcompy-managed sibling nodes

When `_init_node` finds an existing DOM node at an element's `_node_idx` that is not an adoptable prerendered node, it SHALL remove that node only if the node is not webcompy-managed (`__webcompy_node__` is not set). A webcompy-managed node found at the target index SHALL be left in place; the element SHALL create its own node and rely on `_mount_node` to insert it at the correct position via `insertBefore`. Prerendered nodes that do not match the element (tag or node-type mismatch) SHALL still be removed and recreated, since prerendered nodes never carry `__webcompy_node__`. This applies to `ElementBase._init_node`, `TextElement._init_node`, and `RawHTMLElement._init_node`, matching the existing guarded behavior of `NewLine._init_node`.

#### Scenario: Unkeyed for-loop refresh preserves following siblings
- **WHEN** a template contains `{% for item in items %}` over a `ReactiveList` followed by a static sibling element inside the same parent, and the list is mutated (e.g., item appended)
- **THEN** the refreshed DOM SHALL still contain the following sibling at its original position after the rendered items

#### Scenario: Keyed (dict) repeat insertion preserves following siblings
- **WHEN** a `{% for k, v in d %}` over a `ReactiveDict` is followed by a static sibling element and a new key is inserted
- **THEN** the refreshed DOM SHALL contain the new item's element and SHALL still contain the following sibling

#### Scenario: If-branch toggle preserves following siblings
- **WHEN** an `{% if %}` whose branches use non-patchable tags (e.g., `<span>` vs `<em>`) is followed by a static sibling element and the condition signal toggles
- **THEN** the incoming branch's element SHALL be rendered and the following sibling SHALL still be present in the DOM

#### Scenario: MarkdownFor refresh preserves following siblings
- **WHEN** a `MarkdownForElement` over an empty `ReactiveList` is followed by a static sibling element and the first item is appended to the list
- **THEN** the refreshed DOM SHALL contain the rendered `<ul>` before the sibling and SHALL still contain the following sibling at its original position

#### Scenario: Prerendered tag mismatch is still discarded
- **WHEN** hydration encounters a prerendered node at an element's index whose tag does not match the element
- **THEN** the prerendered node SHALL be removed and a fresh node SHALL be created, as before
