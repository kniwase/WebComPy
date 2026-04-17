## ADDED Requirements

### Requirement: ReactiveList shall expose mutation metadata after each mutating operation
Each mutating method on `ReactiveList` (`append`, `extend`, `pop`, `insert`, `sort`, `remove`, `clear`, `reverse`, `__setitem__`) SHALL set a `_last_mutation` attribute on the instance describing the operation type, the affected index, and the value involved. This metadata enables consumers to perform incremental updates instead of full rebuilds.

#### Scenario: Append mutation metadata
- **WHEN** a developer calls `items.append("new_item")` on a `ReactiveList`
- **THEN** `items._last_mutation.op` SHALL be `"append"`
- **AND** `items._last_mutation.index` SHALL be the index of the newly appended item
- **AND** `items._last_mutation.value` SHALL be the appended item

#### Scenario: Pop mutation metadata
- **WHEN** a developer calls `items.pop(1)` on a `ReactiveList`
- **THEN** `items._last_mutation.op` SHALL be `"pop"`
- **AND** `items._last_mutation.index` SHALL be `1`
- **AND** `items._last_mutation.value` SHALL be the popped item

#### Scenario: Insert mutation metadata
- **WHEN** a developer calls `items.insert(0, "first")` on a `ReactiveList`
- **THEN** `items._last_mutation.op` SHALL be `"insert"`
- **AND** `items._last_mutation.index` SHALL be `0`
- **AND** `items._last_mutation.value` SHALL be `"first"`

#### Scenario: Clear mutation metadata
- **WHEN** a developer calls `items.clear()` on a `ReactiveList`
- **THEN** `items._last_mutation.op` SHALL be `"clear"`
- **AND** `items._last_mutation.index` SHALL be `None`
- **AND** `items._last_mutation.value` SHALL be `None`

#### Scenario: Reverse mutation metadata
- **WHEN** a developer calls `items.reverse()` on a `ReactiveList`
- **THEN** `items._last_mutation.op` SHALL be `"reverse"`
- **AND** `items._last_mutation.index` SHALL be `None`
- **AND** `items._last_mutation.value` SHALL be `None`

#### Scenario: Sort mutation metadata
- **WHEN** a developer calls `items.sort()` on a `ReactiveList`
- **THEN** `items._last_mutation.op` SHALL be `"sort"`
- **AND** `items._last_mutation.index` SHALL be `None`
- **AND** `items._last_mutation.value` SHALL be `None`

### Requirement: ReactiveList mutation metadata shall not change the existing callback contract
The `_last_mutation` attribute SHALL be an additional side-channel that does not alter the existing `on_after_updating` callback signature. Existing callbacks registered via `on_after_updating` SHALL continue to receive the same arguments as before and function without modification.

#### Scenario: Existing on_after_updating callback unaffected
- **WHEN** a developer has registered `my_list.on_after_updating(lambda val: print(val))` on a `ReactiveList`
- **AND** calls `my_list.append("new")`
- **THEN** the callback SHALL receive the full list value as before
- **AND** the callback SHALL NOT receive `ListMutation` as an argument