## MODIFIED Requirements

### Requirement: List rendering shall map a reactive list to element templates
The `repeat` construct SHALL take a reactive list, a template function, and an optional `key` function. The `key` function extracts a unique identifier from each list item for reconciliation. When `key` is provided, `RepeatElement` SHALL reuse existing DOM elements for items whose keys persist across mutations, remove elements whose keys are no longer in the list, and create new elements for newly added keys. When `key` is not provided, all rendered items SHALL be removed and regenerated (full rebuild behavior).

#### Scenario: Rendering a list of items with keys
- **WHEN** a developer writes `repeat(items, lambda item: html.LI({}, item.name), key=lambda item: item.id)`
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** only the new `<li>` SHALL be created and appended
- **AND** existing `<li>` elements SHALL remain in the DOM unchanged

#### Scenario: Rendering a list of items without keys (backward compatible)
- **WHEN** a developer writes `repeat(items, lambda item: html.LI({}, item.name))` without a `key` parameter
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** the entire list SHALL be regenerated with the new item included