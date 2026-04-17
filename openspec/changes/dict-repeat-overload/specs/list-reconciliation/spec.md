## MODIFIED Requirements

### Requirement: Key-based reconciliation shall reuse existing DOM elements for list items or dict entries with matching keys
When a `repeat()` is created with a `key` function, an index key, or a `ReactiveDict`, the `RepeatElement` SHALL map each rendered child to its key. Upon mutation, children whose keys still exist in the new list or dict SHALL be reused (their DOM nodes preserved) rather than destroyed and recreated.

#### Scenario: Appending an item to a keyed list
- **WHEN** a developer creates `repeat(items, template, key=lambda item: item.id)` with 3 items
- **AND** appends a 4th item via `items.append(new_item)`
- **THEN** the 3 existing DOM nodes SHALL remain in place (no removal or re-creation)
- **AND** a new DOM node SHALL be created and appended for the 4th item

#### Scenario: Removing an item from a keyed list
- **WHEN** a developer creates `repeat(items, template, key=lambda item: item.id)` with 3 items [A, B, C]
- **AND** removes item B via `items.pop(1)`
- **THEN** the DOM nodes for items A and C SHALL be reused (not removed or re-creation)
- **AND** the DOM node for item B SHALL be removed

#### Scenario: Dict entry addition with keyed reconciliation
- **WHEN** a developer creates `repeat(my_dict, template)` with 3 entries
- **AND** adds a 4th entry via `my_dict["new"] = value`
- **THEN** the 3 existing DOM nodes SHALL remain in place
- **AND** a new DOM node SHALL be created for the new entry

#### Scenario: Dict entry removal with keyed reconciliation
- **WHEN** a developer creates `repeat(my_dict, template)` with entries [A, B, C]
- **AND** removes entry B via `del my_dict["B"]`
- **THEN** the DOM nodes for entries A and C SHALL be reused
- **AND** the DOM node for entry B SHALL be removed