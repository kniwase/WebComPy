# Reactive System

## Purpose

Reactive state is the foundation of a declarative UI. In a traditional imperative approach, the developer must manually synchronize data changes with the DOM — finding the right elements, updating their content, toggling their attributes, and managing the order of updates. A reactive system eliminates this by establishing a dependency graph: when data changes, the system automatically propagates those changes to every part of the UI that depends on them.

WebComPy's reactive system provides primitive containers (`Reactive`), derived values (`Computed`), and collections (`ReactiveList`, `ReactiveDict`) that integrate seamlessly with the element system. Any part of the UI that reads a reactive value is automatically tracked as a dependent, and any change to that value triggers updates in all dependents — whether they are text content, element attributes, computed derivations, or conditional renderings.

**What WebComPy does not yet provide:** In other reactive frameworks like Vue or SolidJS, dict mutations can trigger fine-grained updates for individual items. In WebComPy, `ReactiveDict` is coarse-grained — any mutation triggers a full-collection change notification. `ReactiveList` now exposes granular mutation metadata via `_last_mutation` for incremental consumers, but its core change notification remains full-collection.

## Requirements

### Requirement: Primitive reactive values shall notify dependents on change
A `Reactive` container SHALL hold a single value. When its value is set, all registered dependents SHALL be notified — both before the change (with the old value) and after the change (with the new value).

#### Scenario: Updating a reactive value
- **WHEN** a developer sets `my_reactive.value = "new value"`
- **THEN** any `Computed` or UI element that previously read `my_reactive.value` SHALL be notified with the new value

#### Scenario: Reading a reactive value registers dependency
- **WHEN** a `Computed` function reads `my_reactive.value` during its calculation
- **THEN** that `Computed` SHALL be automatically subscribed to `my_reactive`
- **AND** future changes to `my_reactive` SHALL trigger recalculation of the `Computed`

### Requirement: Computed values shall derive from other reactives automatically
A `Computed` SHALL evaluate a function, automatically discover which reactive values the function reads, and re-evaluate whenever any of those dependencies change.

#### Scenario: Creating a computed full name
- **WHEN** a developer creates `Computed(lambda: f"{first_name.value} {last_name.value}")`
- **THEN** the computed SHALL track `first_name` and `last_name` as dependencies
- **AND** when either changes, the computed SHALL recalculate automatically

### Requirement: Computed properties shall cache lazily on class instances
A `computed_property` decorated on a class SHALL create a `Computed` instance on first access and cache it in the instance's dictionary, so that the computation runs only once per instance and subsequent accesses return the cached value.

#### Scenario: Using computed_property in a class-style component
- **WHEN** a developer accesses `self.full_name` for the first time on a component instance
- **THEN** a `Computed` is created and stored in the instance's `__dict__`
- **WHEN** accessed again on the same instance
- **THEN** the cached `Computed` is returned without re-creation

### Requirement: Reactive collections shall propagate changes
`ReactiveList` and `ReactiveDict` SHALL behave like their standard Python counterparts for reading and mutation, but any mutation operation SHALL trigger change notifications so that dependent UI elements update.

#### Scenario: Appending to a ReactiveList used in a repeat template
- **WHEN** a developer calls `my_list.append(item)` on a `ReactiveList` used in a `repeat()` template
- **THEN** the change notification SHALL cause the list rendering to update

#### Scenario: Setting a key in a ReactiveDict
- **WHEN** a developer calls `my_dict["key"] = value` on a `ReactiveDict`
- **THEN** any computed or UI element that read from `my_dict` SHALL be notified

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

### Requirement: Readonly views shall prevent external mutation of reactive values
A `readonly()` wrapper SHALL provide a reactive value that tracks the source but does not expose a setter, allowing a component to share its state with children without giving them write access.

#### Scenario: Passing reactive state to a child component
- **WHEN** a parent passes `readonly(my_state)` to a child component
- **THEN** the child SHALL be able to read `my_state.value`
- **AND** the child SHALL NOT be able to modify `my_state.value` through the readonly wrapper

### Requirement: The reactive system shall support before-update and after-update callbacks
Developers SHALL be able to register callbacks that fire before a reactive value changes (receiving the old value) and after it changes (receiving the new value), enabling side effects like logging, validation, or conditional DOM manipulation.

#### Scenario: Logging state changes
- **WHEN** a developer registers `my_reactive.on_after_updating(lambda new_val: print(f"Changed to {new_val}"))`
- **THEN** each time `my_reactive.value` is set, the callback SHALL fire with the new value