# List and Dict Reconciliation

## Purpose

List and dict rendering are among the most common UI patterns, and when a reactive collection changes, the framework should reuse existing DOM elements whenever possible rather than destroying and recreating the entire list. Key-based reconciliation allows `repeat()` to match list items or dict entries by a unique identifier, preserving DOM state (focus, input values, scroll position) and reducing the number of DOM operations from O(n) full rebuild to O(changed items).

## Requirements

### Requirement: Key-based reconciliation shall reuse existing DOM elements for list items or dict entries with matching keys
When a `repeat()` is created with a `key` function, an index key, or a `ReactiveDict`, the `RepeatElement` SHALL map each rendered child to its key. This also applies when `repeat()` receives a `ReactiveDict` — dict keys are used directly as reconciliation identifiers. Upon mutation, children whose keys still exist in the new list or dict SHALL be reused (their DOM nodes preserved) rather than destroyed and recreated.

#### Scenario: Appending an item to a keyed list
- **WHEN** a developer creates `repeat(items, template, key=lambda item: item.id)` with 3 items
- **AND** appends a 4th item via `items.append(new_item)`
- **THEN** the 3 existing DOM nodes SHALL remain in place (no removal or re-creation)
- **AND** a new DOM node SHALL be created and appended for the 4th item

#### Scenario: Removing an item from a keyed list
- **WHEN** a developer creates `repeat(items, template, key=lambda item: item.id)` with 3 items [A, B, C]
- **AND** removes item B via `items.pop(1)`
- **THEN** the DOM nodes for items A and C SHALL be reused (not removed or re-created)
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

### Requirement: repeat without a key shall fall back to full rebuild
When a `repeat()` is created without a `key` function, the `RepeatElement` SHALL continue to remove all existing children and regenerate them from scratch on every list mutation, preserving backward compatibility.

#### Scenario: Existing repeat usage without key
- **WHEN** a developer creates `repeat(items, template)` without a `key` parameter
- **AND** mutates the list
- **THEN** all existing children SHALL be removed and regenerated from the template

### Requirement: Duplicate keys shall raise an error
If the `key` function returns the same key value for two or more items in the list, the framework SHALL raise a `WebComPyException` identifying the duplicate keys, preventing undefined reconciliation behavior.

#### Scenario: Key function returns duplicate keys
- **WHEN** a developer creates `repeat(items, template, key=lambda item: item.category)` and two items have the same category
- **THEN** a `WebComPyException` SHALL be raised with a message including the duplicate key value

### Requirement: Reused elements shall preserve their state
When a keyed list item's DOM element is reused during reconciliation, the element's local state (input values, focus state, scroll position, CSS transitions) SHALL be preserved because the DOM node is not removed and re-created.

#### Scenario: Input value preserved on list mutation
- **WHEN** a keyed list renders input elements for each item
- **AND** a user types "hello" into the input for item B
- **AND** a new item is appended to the list
- **THEN** the input for item B SHALL still contain "hello"

### Requirement: Key function shall accept a callable extracting a string or int identifier
The `repeat()` function SHALL accept an optional `key` parameter of type `Callable[[T], str | int]` that extracts a unique identifier from each list item.

#### Scenario: Using a string key
- **WHEN** a developer creates `repeat(users, template, key=lambda u: u.id)` where `u.id` is a string
- **THEN** the string ID SHALL be used to match existing children to list items

#### Scenario: Using an integer key
- **WHEN** a developer creates `repeat(rows, template, key=lambda r: r.pk)` where `r.pk` is an integer
- **THEN** the integer PK SHALL be used to match existing children to list items