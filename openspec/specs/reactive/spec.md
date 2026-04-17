# Reactive System

## Purpose

Reactive state is the foundation of a declarative UI. In a traditional imperative approach, the developer must manually synchronize data changes with the DOM — finding the right elements, updating their content, toggling their attributes, and managing the order of updates. A reactive system eliminates this by establishing a dependency graph: when data changes, the system automatically propagates those changes to every part of the UI that depends on them.

WebComPy's reactive system provides primitive containers (`Reactive`), derived values (`Computed`), and collections (`ReactiveList`, `ReactiveDict`) that integrate seamlessly with the element system. Any part of the UI that reads a reactive value is automatically tracked as a dependent, and any change to that value triggers updates in all dependents — whether they are text content, element attributes, computed derivations, or conditional renderings.

**What WebComPy does not yet provide:** In other reactive frameworks like Vue or SolidJS, list and dict mutations can trigger fine-grained updates for individual items. In WebComPy, `ReactiveList` and `ReactiveDict` are coarse-grained — any mutation triggers a full-collection change notification.

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