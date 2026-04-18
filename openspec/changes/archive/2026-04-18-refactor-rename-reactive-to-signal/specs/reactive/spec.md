## MODIFIED Requirements

### Requirement: Primitive reactive values shall notify dependents on change
A `Signal` container SHALL hold a single value. When its value is set to a different value (determined by equality check), all registered dependents SHALL be notified — both before the change (with the old value) and after the change (with the new value). Setting the same value (where `old is new or old == new`) SHALL NOT trigger notifications.

#### Scenario: Updating a signal value
- **WHEN** a developer sets `my_signal.value = "new value"`
- **THEN** any `Computed` or UI element that previously read `my_signal.value` SHALL be notified with the new value

#### Scenario: Reading a signal value registers dependency
- **WHEN** a `Computed` function reads `my_signal.value` during its calculation
- **THEN** that `Computed` SHALL be automatically subscribed to `my_signal`
- **AND** future changes to `my_signal` SHALL trigger recalculation of the `Computed`

#### Scenario: Setting the same value does not trigger notifications
- **WHEN** a developer sets `my_signal.value = "same"` where `my_signal.value` already equals `"same"`
- **THEN** no `on_after_updating` callbacks SHALL be invoked
- **AND** no downstream dependents SHALL be notified
- **AND** any `Computed` depending on `my_signal` SHALL NOT be marked dirty

#### Scenario: Setting a different but equal object
- **WHEN** a developer creates `my_signal = Signal([1, 2, 3])` and then sets `my_signal.value = [1, 2, 3]` (a new list with equal contents)
- **THEN** the equality check `[1, 2, 3] == [1, 2, 3]` SHALL return True
- **AND** no notifications SHALL be triggered

### Requirement: Computed values shall derive from other signals automatically
A `Computed` SHALL evaluate a function, automatically discover which signal values the function reads, and re-evaluate lazily when any of those dependencies change. Dependencies SHALL be re-tracked on each evaluation, supporting dynamic dependency changes from conditional branching. A `Computed` that has not been read since its last evaluation SHALL NOT re-evaluate, regardless of how many dependencies have changed.

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

#### Scenario: ReactiveList mutation metadata for append
- **WHEN** a developer calls `items.append("new_item")` on a `ReactiveList`
- **THEN** `items._last_mutation.op` SHALL be `"append"`
- **AND** `items._last_mutation.index` SHALL be the index of the newly appended item
- **AND** `items._last_mutation.value` SHALL be the appended item

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

### Requirement: on_after_updating callbacks shall receive the current signal value
The `on_after_updating` method SHALL register a callback that receives the current value of the signal after a change. The `_last_mutation` attribute on `ReactiveList` and `ReactiveDict` SHALL be a separate side-channel for mutation metadata and SHALL NOT be passed as an argument to `on_after_updating` callbacks.

#### Scenario: on_after_updating callback receives the current value
- **WHEN** a developer has registered `my_list.on_after_updating(lambda val: print(val))` on a `ReactiveList`
- **AND** calls `my_list.append("new")`
- **THEN** the callback SHALL receive the current list value
- **AND** the callback SHALL NOT receive `ListMutation` as an argument

### Requirement: Readonly views shall prevent external mutation of signal values
A `readonly()` wrapper SHALL provide a signal value that tracks the source but does not expose a setter, allowing a component to share its state with children without giving them write access.

#### Scenario: Passing signal state to a child component
- **WHEN** a parent passes `readonly(my_state)` to a child component
- **THEN** the child SHALL be able to read `my_state.value`
- **AND** the child SHALL NOT be able to modify `my_state.value` through the readonly wrapper
- **AND** changes to `my_state.value` SHALL propagate to the child via the readonly wrapper

### Requirement: The signal system shall support before-update and after-update callbacks
Developers SHALL be able to register callbacks that fire before a signal value changes (receiving the old value) and after it changes (receiving the new value), enabling side effects like logging, validation, or conditional DOM manipulation. These callbacks SHALL NOT fire when an equality check determines the value has not changed.

#### Scenario: Callbacks not invoked on same-value write
- **WHEN** a developer registers `my_signal.on_after_updating(lambda v: print(v))` and sets `my_signal.value` to its current value
- **THEN** the callback SHALL NOT be invoked

#### Scenario: Callbacks invoked on actual change
- **WHEN** a developer registers `my_signal.on_after_updating(lambda v: print(v))` and sets `my_signal.value = "new"`
- **THEN** the callback SHALL be invoked with `"new"`

### Requirement: Signal graph nodes shall support deterministic cleanup
Each signal node (Signal, Computed, CallbackConsumerNode, effect scope) SHALL maintain its own producer and consumer edges in a linked-list graph structure. Calling `consumer_destroy()` on a node SHALL remove all its edges from the graph, ensuring that destroyed nodes receive no further notifications and cannot leak memory.

#### Scenario: Destroying a computed removes all graph edges
- **WHEN** a `Computed` instance `c` depends on `a` and `b`, and `consumer_destroy()` is called on `c`
- **THEN** `c` SHALL be removed from `a`'s and `b`'s consumer lists
- **AND** changes to `a` and `b` SHALL NOT trigger any computation on `c`

#### Scenario: Destroying a component cleans up all subscriptions
- **WHEN** a component that subscribed to `Signal` values via `effect()` or `on_after_updating` is destroyed
- **THEN** all producer edges from that component's consumer nodes SHALL be removed
- **AND** the destroyed component SHALL NOT receive notifications from previously subscribed signal values

### Requirement: Computed properties shall cache lazily on class instances
A `computed_property` decorated on a class SHALL create a `Computed` instance on first access and cache it in the instance's dictionary, so that the computation runs only once per instance and subsequent accesses return the cached value.

#### Scenario: Using computed_property in a class-style component
- **WHEN** a developer accesses `self.full_name` for the first time on a component instance
- **THEN** a `Computed` is created and stored in the instance's `__dict__`
- **WHEN** accessed again on the same instance
- **THEN** the cached `Computed` is returned without re-creation

## RENAMED Requirements

FROM: Primitive reactive values shall notify dependents on change
TO: Primitive signal values shall notify dependents on change

FROM: Computed values shall derive from other reactives automatically
TO: Computed values shall derive from other signals automatically

FROM: The reactive system shall support before-update and after-update callbacks
TO: The signal system shall support before-update and after-update callbacks

FROM: Reactive graph nodes shall support deterministic cleanup
TO: Signal graph nodes shall support deterministic cleanup

FROM: Computed properties shall cache lazily on class instances
TO: Computed properties shall cache lazily on class instances (unchanged — no rename needed)