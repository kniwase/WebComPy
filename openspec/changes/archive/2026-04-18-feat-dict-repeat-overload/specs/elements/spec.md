## MODIFIED Requirements

### Requirement: List and dict rendering shall map reactive collections to element templates with type-safe overloads
The `repeat` construct SHALL support five type-safe overload signatures:

1. `repeat(ReactiveDict[K, V], template: (V,) -> ChildNode)` — dict value-only, keyed by dict keys
2. `repeat(ReactiveDict[K, V], template: (V, K) -> ChildNode)` — dict value+key, keyed by dict keys
3. `repeat(ReactiveList[V], template: (V,) -> ChildNode)` — list unkeyed (backward compatible, full rebuild)
4. `repeat(ReactiveList[V], template: (V, int) -> ChildNode)` — list with index as key
5. `repeat(ReactiveList[V], template: (V, K) -> ChildNode), key: (V) -> K)` — list with custom key function

When `key` is provided (overloads 2, 4, 5) or dict mode is used (overloads 1, 2), `RepeatElement` SHALL reuse existing DOM elements for items whose keys persist across mutations. When no `key` is provided and single-arg template is used (overload 3), all rendered items SHALL be removed and regenerated (full rebuild behavior).

#### Scenario: Rendering a list of items with key function
- **WHEN** a developer writes `repeat(items, lambda item, id: html.LI({"data-id": id}, item.name), key=lambda item: item.id)`
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** only the new `<li>` SHALL be created and appended
- **AND** existing `<li>` elements SHALL remain in the DOM unchanged

#### Scenario: Rendering a list of items without keys (backward compatible)
- **WHEN** a developer writes `repeat(items, lambda item: html.LI({}, item.name))` without a `key` parameter
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** the entire list SHALL be regenerated with the new item included

#### Scenario: Rendering a ReactiveDict with value-only template
- **WHEN** a developer writes `repeat(my_dict, lambda value: html.LI({}, value))`
- **THEN** one `<li>` SHALL be rendered for each value in `my_dict`
- **AND** dict keys SHALL be used as reconciliation identifiers for efficient DOM updates

#### Scenario: Rendering a ReactiveDict with value-key template
- **WHEN** a developer writes `repeat(my_dict, lambda value, key: html.LI({}, f"{key}: {value}"))`
- **THEN** one `<li>` SHALL be rendered for each key-value pair in `my_dict`
- **AND** dict keys SHALL be used as reconciliation identifiers for efficient DOM updates