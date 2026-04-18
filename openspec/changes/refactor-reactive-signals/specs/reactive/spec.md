# Reactive System (Modified)

## MODIFIED Requirements

### Requirement: Primitive reactive values shall notify dependents on change
A `Reactive` container SHALL hold a single value. When its value is set to a different value (determined by equality check), all registered dependents SHALL be notified — both before the change (with the old value) and after the change (with the new value). Setting the same value (where `old is new or old == new`) SHALL NOT trigger notifications.

#### Scenario: Updating a reactive value
- **WHEN** a developer sets `my_reactive.value = "new value"`
- **THEN** any `Computed` or UI element that previously read `my_reactive.value` SHALL be notified with the new value

#### Scenario: Reading a reactive value registers dependency
- **WHEN** a `Computed` function reads `my_reactive.value` during its calculation
- **THEN** that `Computed` SHALL be automatically subscribed to `my_reactive`
- **AND** future changes to `my_reactive` SHALL trigger recalculation of the `Computed`

#### Scenario: Setting the same value does not trigger notifications
- **WHEN** a developer sets `my_reactive.value = "same"` where `my_reactive.value` already equals `"same"`
- **THEN** no `on_after_updating` callbacks SHALL be invoked
- **AND** no downstream dependents SHALL be notified
- **AND** any `Computed` depending on `my_reactive` SHALL NOT be marked dirty

#### Scenario: Setting a different but equal object
- **WHEN** a developer creates `my_reactive = Reactive([1, 2, 3])` and then sets `my_reactive.value = [1, 2, 3]` (a new list with equal contents)
- **THEN** the equality check `[1, 2, 3] == [1, 2, 3]` SHALL return True
- **AND** no notifications SHALL be triggered

### Requirement: Computed values shall derive from other reactives automatically
A `Computed` SHALL evaluate a function, automatically discover which reactive values the function reads, and re-evaluate lazily when any of those dependencies change. Dependencies SHALL be re-tracked on each evaluation, supporting dynamic dependency changes from conditional branching. A `Computed` that has not been read since its last evaluation SHALL NOT re-evaluate, regardless of how many dependencies have changed.

#### Scenario: Creating a computed full name
- **WHEN** a developer creates `Computed(lambda: f"{first_name.value} {last_name.value}")`
- **THEN** the computed SHALL track `first_name` and `last_name` as dependencies

#### Scenario: Computed updates on dependency change
- **WHEN** `first_name.value` is set to a new value
- **THEN** the computed SHALL be marked dirty
- **AND** the next read of `computed.value` SHALL return the updated result
- **AND** the computation function SHALL execute at most once for that read

#### Scenario: Computed does not recompute when unread
- **WHEN** a computed depends on `a` and `b`, and `a.value` changes multiple times without anyone reading `computed.value`
- **THEN** the computed SHALL NOT execute its computation function
- **AND** reading `computed.value` after the changes SHALL return the correct result with a single recomputation

#### Scenario: Computed does not propagate when result is unchanged
- **WHEN** a computed returns the same value as before (e.g., `Computed(lambda: abs(x.value))` and `x` changes from `-5` to `5`)
- **THEN** the computed SHALL NOT increment its version
- **AND** downstream dependents (other Computed values, effects) SHALL NOT be notified

#### Scenario: Dynamic dependency tracking with conditional branching
- **WHEN** a developer creates `Computed(lambda: a.value if flag.value else b.value)` with `flag.value == True`
- **AND** the computed initially tracks `flag` and `a` as dependencies (not `b`)
- **AND** `flag.value` is set to `False`
- **THEN** the next evaluation SHALL read `b.value` instead of `a.value`
- **AND** `b` SHALL be added to the computed's producer edges
- **AND** `a` SHALL be removed from the computed's producer edges
- **AND** subsequent changes to `a.value` SHALL NOT trigger recomputation

### Requirement: Reactive collections shall propagate changes
`ReactiveList` and `ReactiveDict` SHALL behave like their standard Python counterparts for reading and mutation, but any mutation operation SHALL trigger change notifications so that dependent UI elements update. `ReactiveList` and `ReactiveDict` SHALL expose `_last_mutation` metadata after each mutating operation, enabling incremental consumers to determine what changed without comparing the full collection. Mutation methods (`append`, `__setitem__`, etc.) on `ReactiveList` and `ReactiveDict` SHALL always trigger change notifications regardless of equality, since they represent in-place mutations.

#### Scenario: ReactiveList mutation always propagates
- **WHEN** a developer calls `my_list.append(item)` and the appended item is identical to the last item in the list
- **THEN** change notifications SHALL still be triggered (mutation methods bypass equality check)

#### Scenario: ReactiveList set_value with equal list skips propagation
- **WHEN** a developer sets `my_list.value = [1, 2, 3]` and the current value is already `[1, 2, 3]`
- **THEN** the equality check `[1, 2, 3] == [1, 2, 3]` SHALL skip propagation

### Requirement: Readonly views shall prevent external mutation of reactive values
A `readonly()` wrapper SHALL provide a reactive value that tracks the source but does not expose a setter, allowing a component to share its state with children without giving them write access.

#### Scenario: Passing reactive state to a child component
- **WHEN** a parent passes `readonly(my_state)` to a child component
- **THEN** the child SHALL be able to read `my_state.value`
- **AND** the child SHALL NOT be able to modify `my_state.value` through the readonly wrapper
- **AND** changes to `my_state.value` SHALL propagate to the child via the readonly wrapper

### Requirement: The reactive system shall support before-update and after-update callbacks
Developers SHALL be able to register callbacks that fire before a reactive value changes (receiving the old value) and after it changes (receiving the new value), enabling side effects like logging, validation, or conditional DOM manipulation. These callbacks SHALL NOT fire when an equality check determines the value has not changed.

#### Scenario: Callbacks not invoked on same-value write
- **WHEN** a developer registers `my_reactive.on_after_updating(lambda v: print(v))` and sets `my_reactive.value` to its current value
- **THEN** the callback SHALL NOT be invoked

#### Scenario: Callbacks invoked on actual change
- **WHEN** a developer registers `my_reactive.on_after_updating(lambda v: print(v))` and sets `my_reactive.value = "new"`
- **THEN** the callback SHALL be invoked with `"new"`

### Requirement: Reactive graph nodes shall support deterministic cleanup
Each reactive node (Reactive, Computed, CallbackConsumerNode, effect scope) SHALL maintain its own producer and consumer edges in a linked-list graph structure. Calling `consumer_destroy()` on a node SHALL remove all its edges from the graph, ensuring that destroyed nodes receive no further notifications and cannot leak memory.

#### Scenario: Destroying a computed removes all graph edges
- **WHEN** a `Computed` instance `c` depends on `a` and `b`, and `consumer_destroy()` is called on `c`
- **THEN** `c` SHALL be removed from `a`'s and `b`'s consumer lists
- **AND** changes to `a` and `b` SHALL NOT trigger any computation on `c`

#### Scenario: Destroying a component cleans up all subscriptions
- **WHEN** a component that subscribed to `Reactive` values via `effect()` or `on_after_updating` is destroyed
- **THEN** all producer edges from that component's consumer nodes SHALL be removed
- **AND** the destroyed component SHALL NOT receive notifications from previously subscribed reactive values