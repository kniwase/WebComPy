# Reactive System

## Overview

The reactive system is the backbone of WebComPy, providing fine-grained reactivity for UI state management. It uses a global singleton `ReactiveStore` for dependency tracking and change propagation.

## Key Types

### ReactiveStore (Singleton)

- Instantiated at module level via `@_instantiate` decorator (`_base.py`)
- Maintains a registry of all `ReactiveBase` instances (`__instances` dict by ID)
- Manages before/after update callbacks (`__on_before_updating`, `__on_after_updating`)
- Tracks dependencies during computation via `__dependency` list
- **`add_reactive_instance(reactive)`**: Assigns a unique ID and registers the instance
- **`detect_dependency(func)`**: Executes `func`, captures reactive values read during execution, returns `(value, dependencies)` deduplicated
- **`callback_after_updating / callback_before_updating`**: Fires all registered callbacks for an instance
- **`remove_callback(callback_id)`**: Deregisters a callback

### ReactiveBase[V] (Abstract Base)

- **`_value: V`**: The stored value
- **`__reactive_id__: int`**: Unique instance ID
- **`_store`** (ClassVar): Points to the singleton `ReactiveStore`
- **`_change_event`** (static decorator): Wraps a method to call `callback_before_updating(old_value)`, execute the method, then `callback_after_updating(new_value)`
- **`_get_evnet`** (static decorator): Wraps a property getter to register itself in the current dependency context via `ReactiveStore.resister()`
- **`on_after_updating(func)` / `on_before_updating(func)`**: Register callbacks, return callback IDs

### Reactive[V]

- Mutable reactive cell extending `ReactiveBase`
- **`value`** property: getter uses `_get_evnet` for dependency tracking, setter uses `_change_event` for notification
- **`set_value(new_value)`**: Method alternative to setter, decorated with `_change_event`

### Computed[V]

- Derived reactive value extending `ReactiveBase`
- Constructed with `func: Callable[[], V]`
- On `__init__`, calls `_store.detect_dependency(func)` to determine dependencies, then subscribes to each dependency via `on_after_updating(self._compute)`
- When any dependency changes, `_compute()` is called, re-evaluates `func()`, updates `_value`, triggering downstream callbacks
- **`computed(func)`**: Convenience factory function
- **`computed_property(method)`**: Class decorator that lazily creates a `Computed` on first access and caches it in `instance.__dict__` (similar to Python's `@property`)

### ReactiveDict[K, V]

- Extends `Reactive[dict[K, V]]`
- Mutating methods decorated with `@ReactiveBase._change_event`: `__setitem__`, `__delitem__`, `pop`
- Read methods decorated with `@ReactiveBase._get_evnet`: `__getitem__`, `__len__`, `__iter__`, `get`, `keys`, `values`, `items`
- Optional init value (defaults to `{}`)

### ReactiveList[V]

- Extends `Reactive[list[V]]`
- Mutating methods: `append`, `extend`, `pop`, `insert`, `sort`, `reverse`, `clear`, `remove`, `__setitem__`
- Read methods: `index`, `count`, `__getitem__`, `__len__`, `__iter__`

### ReadonlyReactive[V]

- Extends `Computed[V]`, cannot be instantiated directly (`__init__` raises `NotImplementedError`)
- Created via `readonly(reactive_obj)`, which calls `ReadonlyReactive.__create_instance__(reactive)` to create a `Computed(lambda: reactive.value)`

### ReactiveReceivable (Mixin)

- Overrides `__setattr__` to track `ReactiveBase` instances in `__reactive_members__` (a `WeakValueDictionary`)
- `__purge_reactive_members__()`: Currently a no-op (only checks `hasattr`)

## Change Propagation

1. A `Reactive`'s `.value` is set
2. `ReactiveBase._change_event` calls `ReactiveStore.callback_before_updating(old_value)`, then the setter, then `callback_after_updating(new_value)`
3. Any `Computed` subscribed to this reactive gets its `_compute` called
4. Any `Element` that registered an `on_after_updating` callback gets notified
5. `_get_evnet` on `.value` access registers the caller as a dependency

## Design Constraints

- The `ReactiveStore` is a global singleton; all reactive instances share it
- `_get_evnet` (typo for `_get_event`) is consistently used throughout the codebase
- `ReactiveList` / `ReactiveDict` are coarse-grained: any mutation triggers a full-list/dict change notification; there is no element-level reactivity
- `__purge_reactive_members__` is essentially a no-op; reactive member cleanup relies on Python garbage collection