## MODIFIED Requirements

### Requirement: Reactive collections shall propagate changes
`ReactiveList` and `ReactiveDict` SHALL behave like their standard Python counterparts for reading and mutation, but any mutation operation SHALL trigger change notifications so that dependent UI elements update. `ReactiveDict` now also exposes `_last_mutation` metadata after each mutating operation, enabling incremental consumers to determine what changed without comparing the full dict.

#### Scenario: Appending to a ReactiveList used in a repeat template
- **WHEN** a developer calls `my_list.append(item)` on a `ReactiveList` used in a `repeat()` template
- **THEN** the change notification SHALL cause the list rendering to update

#### Scenario: Setting a key in a ReactiveDict
- **WHEN** a developer calls `my_dict["key"] = value` on a `ReactiveDict`
- **THEN** any computed or UI element that read from `my_dict` SHALL be notified

#### Scenario: ReactiveDict mutation metadata for set
- **WHEN** a developer calls `my_dict["key1"] = "value1"` on a `ReactiveDict`
- **THEN** `my_dict._last_mutation` SHALL be a `DictMutation` with `op="set"`, `key="key1"`, `value="value1"`