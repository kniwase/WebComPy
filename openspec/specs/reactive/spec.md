# Signal System

## Purpose

Signal state is the foundation of a declarative UI. In a traditional imperative approach, the developer must manually synchronize data changes with the DOM — finding the right elements, updating their content, toggling their attributes, and managing the order of updates. A signal system eliminates this by establishing a dependency graph: when data changes, the system automatically propagates those changes to every part of the UI that depends on them.

WebComPy's signal system provides primitive containers (`Signal`), derived values (`Computed`), and collections (`ReactiveList`, `ReactiveDict`) that integrate seamlessly with the element system. Any part of the UI that reads a signal value is automatically tracked as a dependent, and any change to that value triggers updates in all dependents — whether they are text content, element attributes, computed derivations, or conditional renderings.

**What WebComPy does not yet provide:** `ReactiveList` and `ReactiveDict` both now expose granular mutation metadata via `_last_mutation` for incremental consumers, but their core change notification remains full-collection. Per-key reactive subscriptions inside `ReactiveDict` are not yet available.

## Requirements

### Requirement: Primitive signal values shall notify dependents on change
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

### Requirement: Computed values shall be created via use_computed()

The function-style creation API for `Computed` SHALL be `use_computed(factory)`. The `Computed` class SHALL remain accessible from `webcompy.signal` as a type annotation (`Computed[T]`) and for framework internal use. `use_computed()` SHALL also be importable from `webcompy` top-level alongside `use_state()`, `use_reactive_list()`, and `use_reactive_dict()`.

#### Scenario: Creating a computed value with use_computed()
- **WHEN** a developer writes `doubled = use_computed(lambda: count.value * 2)` inside a component setup function
- **THEN** a `Computed[int]` SHALL be returned
- **AND** the factory SHALL execute eagerly during construction, establishing `count` as a tracked dependency

#### Scenario: use_computed() is importable from webcompy top-level
- **WHEN** a developer writes `from webcompy import use_computed`
- **THEN** `use_computed` SHALL be available
- **AND** `computed` SHALL NOT be available from `webcompy` or `webcompy.signal`

#### Scenario: Computed class remains for type annotations
- **WHEN** a developer writes `doubled: Computed[int] = use_computed(lambda: count.value * 2)`
- **THEN** the type annotation SHALL be valid
- **AND** `Computed` SHALL remain importable from `webcompy.signal`

### Requirement: Signal and Computed classes are internal types

The `Signal` and `Computed` classes SHALL be internal implementation types accessible through `webcompy.signal`. They SHALL NOT emit runtime deprecation warnings when constructed directly. The `use_state()` and `use_computed()` composables SHALL be the public creation APIs, using `Signal()` and `Computed()` constructors internally.

#### Scenario: Signal() constructor is not warned
- **WHEN** framework internal or extension code calls `Signal(0)`
- **THEN** the `Signal` SHALL be created without any warning

#### Scenario: Computed() constructor is not warned
- **WHEN** framework internal or extension code calls `Computed(fn)`
- **THEN** the `Computed` SHALL be created without any warning

### Requirement: Computed properties shall cache lazily on class instances
A `computed_property` decorated on a class SHALL create a `Computed` instance on first access and cache it in the instance's dictionary, so that the computation runs only once per instance and subsequent accesses return the cached value.

#### Scenario: Using computed_property in a class-style component
- **WHEN** a developer accesses `self.full_name` for the first time on a component instance
- **THEN** a `Computed` is created and stored in the instance's `__dict__`
- **WHEN** accessed again on the same instance
- **THEN** the cached `Computed` is returned without re-creation

### Requirement: Signal collections shall propagate changes
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

### Requirement: on_after_updating callbacks shall receive the current signal value
The `on_after_updating` method SHALL register a callback that receives the current value of the reactive after a change. The `_last_mutation` attribute on `ReactiveList` and `ReactiveDict` SHALL be a separate side-channel for mutation metadata and SHALL NOT be passed as an argument to `on_after_updating` callbacks.

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

### Requirement: SignalReceivable shall track signal members by attribute name

`SignalReceivable.__signal_members__` SHALL be a `dict[str, SignalBase]` mapping attribute name to the Signal instance assigned to that attribute. `__setattr__` SHALL call `__set_signal_member__(name, value)` when the value is a `SignalBase` instance, passing the attribute name. `computed_property` SHALL register its `Computed` instances by the method name, consistent with the attribute-name keying.

#### Scenario: Signal assigned to self is tracked by name
- **WHEN** a component executes `self.count = Signal(0)`
- **THEN** `self.__signal_members__["count"]` SHALL reference the `Signal` instance

#### Scenario: Computed property is tracked by name
- **WHEN** a component has a `@computed_property` method named `doubled`
- **AND** the property is accessed (triggering Computed creation)
- **THEN** `self.__signal_members__["doubled"]` SHALL reference the `Computed` instance

#### Scenario: Reassigning a Signal attribute updates the registry
- **WHEN** a component executes `self.count = Signal(0)` then `self.count = Signal(5)`
- **THEN** `self.__signal_members__["count"]` SHALL reference the second `Signal(5)` instance
- **AND** the first `Signal(0)` instance SHALL no longer be in the registry

#### Scenario: Non-Signal attributes are not tracked
- **WHEN** a component executes `self.name = "Alice"` (a plain string)
- **THEN** `self.__signal_members__` SHALL NOT contain `"name"`

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

### Requirement: The signal system shall support before-update and after-update callbacks
Developers SHALL be able to register callbacks that fire before a signal value changes (receiving the old value) and after it changes (receiving the new value), enabling side effects like logging, validation, or conditional DOM manipulation. These callbacks SHALL NOT fire when an equality check determines the value has not changed.

#### Scenario: Logging state changes
- **WHEN** a developer registers `my_signal.on_after_updating(lambda new_val: print(f"Changed to {new_val}"))`
- **THEN** each time `my_signal.value` is set to a different value, the callback SHALL fire with the new value

### Requirement: CallbackConsumerNode shall bind to a SignalBase producer

`CallbackConsumerNode` SHALL type its `_producer` field (and its constructor `producer` parameter) as `SignalBase[Any]`, not the broader `SignalNode` base. Callback consumers are created exclusively by `SignalBase.on_before_updating` / `on_after_updating`, which pass `self` (a value-bearing `SignalBase`) as the producer, and `Computed` — the only other producer that participates in dispatch logic — is itself a `Computed(SignalBase[V])`. Because `_dispatch` reads `self._producer._value` (an attribute defined on `SignalBase`, absent on the `SignalNode` base), the declared producer type SHALL be `SignalBase[Any]` so the access is type-valid without a runtime `isinstance` branch or `cast`.

#### Scenario: Dispatch reads the producer value without a type warning
- **WHEN** `CallbackConsumerNode._dispatch` executes and reads `self._producer._value`
- **THEN** `uv run pyright` SHALL report no `reportAttributeAccessIssue` warning
- **AND** no `isinstance(self._producer, SignalBase)` runtime branch SHALL be required to satisfy the type checker

#### Scenario: Producer retyping remains compatible with the signal graph API
- **WHEN** `CallbackConsumerNode.__init__` registers the producer via `producer_add_live_consumer(producer, self)`
- **THEN** the call SHALL remain valid because `SignalBase` is a subclass of `SignalNode`
- **AND** `producer_update_value_version(self._producer)` SHALL remain valid for the same reason

#### Scenario: Computed producer is accepted unchanged
- **WHEN** a `Computed` (which extends `SignalBase[V]`) is the producer of a `CallbackConsumerNode`
- **THEN** the retyped `_producer: SignalBase[Any]` field SHALL accept it without coercion
- **AND** the existing `isinstance(self._producer, Computed)` short-circuit in `_dispatch` SHALL continue to work

### Requirement: A producer cleaned within the current epoch SHALL NOT retain a stale dirty flag

`producer_update_value_version()` SHALL clear the producer's `dirty` flag whenever it returns on the `_epoch == last_clean_epoch` early-return path. That condition means the producer's value has already been brought current for the current epoch (either recomputed or marked clean), so any residual `dirty = True` set by a mid-sweep re-mark from a second producer path is stale and MUST NOT survive the call. Leaving `dirty` set would cause the next mutation's `producer_notify_consumers()` to skip this node — its collection step only gathers consumers where `dirty` is `False` — thereby stranding the producer out of the notification sweep and freezing its downstream consumers.

This invariant applies to any `SignalNode` acting as a producer (including `Computed`), and is observable in diamond topologies where a node has two or more producers and is re-marked dirty after being cleaned within the same epoch.

#### Scenario: Cleaned-then-remarked Computed is notified on the next mutation
- **WHEN** a `Computed` `C` has two producers `A` and `B` (diamond topology) and a downstream consumer `D` reads `C`
- **AND** within epoch `E`, `C` is cleaned (`C.last_clean_epoch = E`, `C.dirty = False`) and subsequently re-marked dirty by the second producer path (`C.dirty = True`) during the same notification sweep
- **AND** `producer_update_value_version(C)` is then called while `_epoch == C.last_clean_epoch`
- **THEN** the call SHALL set `C.dirty = False` before returning
- **AND** on the next mutation (epoch advances), `producer_notify_consumers` SHALL collect `C` (because `C.dirty` is `False`) and mark it dirty, propagating to `D`
- **AND** `D` SHALL receive the notification and observe `C`'s updated value

#### Scenario: Stale dirty flag does not strand a diamond consumer
- **WHEN** the bug is present (the early-return leaves `dirty = True`)
- **AND** two rapid mutations occur across epochs on the shared root of a diamond
- **THEN** the downstream consumer `D` would stop receiving updates after the first re-mark, leaving stale UI
- **AND** after the fix, `D` SHALL continue to receive an update on every subsequent mutation that reaches the diamond root

#### Scenario: Single-producer Computed is unaffected
- **WHEN** a `Computed` has exactly one producer and is cleaned within an epoch
- **THEN** `producer_update_value_version` on the early-return path SHALL still clear `dirty` (a no-op since it is already `False`)
- **AND** observable propagation behavior SHALL be unchanged

### Requirement: The notification sweep SHALL NOT re-mark a consumer already clean for the current epoch

`producer_notify_consumers()` SHALL, at mark time (not collection time), skip re-marking any collected consumer whose `last_clean_epoch` equals the current `_epoch`, clearing its `dirty` flag — and SHALL still propagate the notification to that consumer's own consumers (via `consumer_mark_dirty`), so nodes that depend on it receive the sweep's updates. A consumer cleaned within the current epoch has already incorporated every mutation of that sweep; re-marking it would dispatch a duplicate same-epoch notification and, in nested topologies, leave it stuck-dirty because the duplicate dispatch's version check short-circuits before the node is re-read. The propagation re-applies the gate at every level: consumers of the skipped node that are themselves clean for the epoch are skipped in turn (no duplicate dispatch, no residue), while consumers not yet brought current are marked and dispatched exactly once. The gate SHALL NOT recompute or read any node, and SHALL NOT modify the collection predicate (`if not consumer.dirty`).

#### Scenario: Nested Computed chain updates a downstream callback on every mutation
- **WHEN** a source `Signal` feeds two `Computed` producers (`left`, `right`), which feed an `inner` `Computed`, which feeds an `outer` `Computed`, and a callback subscribes to `outer` (nested diamond)
- **AND** the source is mutated across two epochs without reading `outer.value` in between
- **THEN** the callback SHALL fire exactly once per mutation and observe the updated value for both mutations (no silent stale UI)
- **AND** after each sweep, every node in the chain SHALL have `dirty = False` (no stuck residue)

#### Scenario: Cleaned-then-remarked node is not re-marked mid-sweep
- **WHEN** a consumer in a diamond is cleaned for epoch `E` during the first producer path's dispatch
- **AND** the second producer path's collection loop reaches it within the same sweep
- **THEN** the sweep SHALL NOT mark it dirty again or dispatch it a second time
- **AND** its `dirty` flag SHALL remain `False` for the rest of the epoch

#### Scenario: Consumer of a mid-sweep-cleaned node still receives the notification
- **WHEN** a node `C` in a diamond is eagerly recomputed and cleaned for epoch `E` during the first producer path's dispatch, and its value changes (version bumps)
- **AND** a consumer `E` depends only on `C` — it is reachable through no other path of the sweep
- **THEN** the sweep SHALL mark `E` and dispatch its callback exactly once with the updated value (the gate skips `C` itself but propagates to `C`'s consumers)
- **AND** `C` SHALL remain `dirty = False` for the rest of the epoch

#### Scenario: Sweep performs no recomputation
- **WHEN** a notification sweep processes a graph containing dirty `Computed` nodes
- **THEN** the sweep itself SHALL NOT execute any computation function
- **AND** `Computed` values SHALL only be recomputed when read (lazy evaluation is preserved)

#### Scenario: Mid-sweep-registered consumer is not notified for the in-flight mutation
- **WHEN** a consumer is registered on a producer while a notification sweep for that producer is already in progress (its `last_clean_epoch` is the current `_epoch` at registration)
- **THEN** the sweep SHALL NOT mark or dispatch that consumer for the in-flight mutation
- **AND** the consumer SHALL receive notifications for subsequent mutations