## Purpose

Dict repeat enables efficient DOM reconciliation for data naturally modeled as key-value maps. When a `ReactiveDict` is used with `repeat()`, the dict keys serve as reconciliation identifiers, allowing the framework to reuse existing DOM elements when entries are added, removed, or reordered — preserving input state, focus, and scroll position without full rebuilds.

## Requirements

### Requirement: ReactiveDict shall expose mutation metadata after each mutating operation
Each mutating method on `ReactiveDict` (`__setitem__`, `__delitem__`, `pop`, `clear`) SHALL set a `_last_mutation` attribute on the instance describing the operation type, the affected key, and the value involved. This metadata enables consumers to perform incremental updates instead of full rebuilds.

#### Scenario: Set item mutation metadata
- **WHEN** a developer calls `my_dict["key1"] = "value1"` on a `ReactiveDict`
- **THEN** `my_dict._last_mutation.op` SHALL be `"set"`
- **AND** `my_dict._last_mutation.key` SHALL be `"key1"`
- **AND** `my_dict._last_mutation.value` SHALL be `"value1"`

#### Scenario: Delete item mutation metadata
- **WHEN** a developer calls `del my_dict["key1"]` on a `ReactiveDict`
- **THEN** `my_dict._last_mutation.op` SHALL be `"delete"`
- **AND** `my_dict._last_mutation.key` SHALL be `"key1"`
- **AND** `my_dict._last_mutation.value` SHALL be the value that was at `"key1"`

#### Scenario: Pop mutation metadata
- **WHEN** a developer calls `my_dict.pop("key1")` on a `ReactiveDict`
- **THEN** `my_dict._last_mutation.op` SHALL be `"pop"`
- **AND** `my_dict._last_mutation.key` SHALL be `"key1"`
- **AND** `my_dict._last_mutation.value` SHALL be the popped value

#### Scenario: Clear mutation metadata
- **WHEN** a developer calls `my_dict.clear()` on a `ReactiveDict`
- **THEN** `my_dict._last_mutation.op` SHALL be `"clear"`
- **AND** `my_dict._last_mutation.key` SHALL be `None`
- **AND** `my_dict._last_mutation.value` SHALL be `None`

### Requirement: DictMutation metadata shall not change the existing callback contract
The `_last_mutation` attribute SHALL be an additional side-channel that does not alter the existing `on_after_updating` callback signature. Existing callbacks registered via `on_after_updating` SHALL continue to receive the same arguments as before and function without modification.

#### Scenario: Existing on_after_updating callback unaffected
- **WHEN** a developer has registered `my_dict.on_after_updating(lambda val: print(val))` on a `ReactiveDict`
- **AND** calls `my_dict["key1"] = "value1"`
- **THEN** the callback SHALL receive the full dict value as before
- **AND** the callback SHALL NOT receive `DictMutation` as an argument

### Requirement: repeat() shall accept ReactiveDict with type-safe overloads
The `repeat()` function SHALL accept a `ReactiveDict[K, V]` as its first argument, where K is `str | int`. Two overloads are provided for dict mode:
- `repeat(dict, template)` where `template: (V,) -> ChildNode` — value only
- `repeat(dict, template)` where `template: (V, K) -> ChildNode` — value and key

The dict keys SHALL be used as reconciliation identifiers — no separate `key` function is needed or allowed for dict mode.

#### Scenario: Rendering a ReactiveDict with value-key template
- **WHEN** a developer writes `repeat(my_dict, lambda value: html.LI({}, value))`
- **THEN** one `<li>` SHALL be rendered for each value in `my_dict`
- **AND** dict keys SHALL be used as reconciliation identifiers

#### Scenario: Rendering a ReactiveDict with two-argument template
- **WHEN** a developer writes `repeat(my_dict, lambda value, key: html.LI({}, f"{key}: {value}"))`
- **THEN** one `<li>` SHALL be rendered for each key-value pair in `my_dict`
- **AND** dict keys SHALL be used as reconciliation identifiers

#### Scenario: Adding an entry to a ReactiveDict used in repeat()
- **WHEN** a developer has `repeat(my_dict, template)` rendering 3 items
- **AND** calls `my_dict["new_key"] = new_value`
- **THEN** the 3 existing DOM nodes SHALL remain in place (no removal or re-creation)
- **AND** a new DOM node SHALL be created for the new entry

#### Scenario: Deleting an entry from a ReactiveDict used in repeat()
- **WHEN** a developer has `repeat(my_dict, template)` rendering items with keys [A, B, C]
- **AND** calls `del my_dict["B"]`
- **THEN** the DOM nodes for keys A and C SHALL be reused (not removed or re-created)
- **AND** the DOM node for key B SHALL be removed

#### Scenario: Reordering entries in a ReactiveDict used in repeat()
- **WHEN** a developer has `repeat(my_dict, template)` rendering items in order [A, B, C]
- **AND** the dict is reordered such that iteration yields [C, A, B]
- **THEN** the DOM nodes for keys A, B, C SHALL be reused (not removed or re-created)
- **AND** the DOM nodes SHALL be reordered in the DOM to match the new iteration order

### Requirement: repeat() shall accept ReactiveList with type-safe overloads
The `repeat()` function SHALL accept a `ReactiveList[V]` with three overloads:
- `repeat(list, template)` where `template: (V,) -> ChildNode` — unkeyed, full rebuild on mutation
- `repeat(list, template)` where `template: (V, int) -> ChildNode` — keyed by list index
- `repeat(list, template, key)` where `template: (V, K) -> ChildNode` and `key: (V) -> K` — keyed by custom key function

When a `key` function is provided or list index mode is used, `RepeatElement` SHALL reuse existing DOM elements for items whose keys persist across mutations. When no `key` is provided and single-arg template is used, all rendered items SHALL be removed and regenerated (full rebuild behavior).

#### Scenario: Rendering a list of items with key function
- **WHEN** a developer writes `repeat(items, lambda item, id: html.LI({}, item.name), key=lambda item: item.id)`
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** only the new `<li>` SHALL be created and appended
- **AND** existing `<li>` elements SHALL remain in the DOM unchanged

#### Scenario: Rendering a list of items without keys (backward compatible)
- **WHEN** a developer writes `repeat(items, lambda item: html.LI({}, item.name))` without a `key` parameter
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** the entire list SHALL be regenerated with the new item included

### Requirement: Dict repeat keys shall be str or int
The `repeat()` overload for `ReactiveDict` SHALL accept dicts whose keys are `str` or `int`. This matches the key constraint of keyed list reconciliation and ensures keys can be used as DOM element identifiers.

#### Scenario: Using string keys
- **WHEN** a developer creates `repeat(todo_dict, template)` where `todo_dict` is `ReactiveDict[str, V]`
- **THEN** the string keys SHALL be used to match existing children to dict entries

#### Scenario: Using integer keys
- **WHEN** a developer creates `repeat(number_dict, template)` where `number_dict` is `ReactiveDict[int, V]`
- **THEN** the integer keys SHALL be used to match existing children to dict entries

### Requirement: Dict repeat shall preserve state of reused elements
When a keyed dict entry's DOM element is reused during reconciliation, the element's local state (input values, focus state, scroll position) SHALL be preserved because the DOM node is not removed and re-created.

#### Scenario: Input value preserved on dict mutation
- **WHEN** a dict repeat renders input elements for each entry
- **AND** a user types "hello" into the input for key "item-b"
- **AND** a new entry is added to the dict
- **THEN** the input for key "item-b" SHALL still contain "hello"