---
title: Reactivity API
description: API reference for webcompy.signal reactive containers, computed signals, effects, collections, and composables.
---

# Reactivity API

<!-- author:start:intro -->
API reference for `webcompy.signal`: mutable signals, computed derivations, reactive lists and dicts, readonly projections, effects, transfer composables (`use_state`, `use_reactive_list`, `use_reactive_dict`), and internal graph tracking (`SignalNode`).
<!-- author:end:intro -->

<!-- generated:start -->

## Signals, Computed & Collections

### Computed

```python
class Computed(SignalBase[V]):
    def __init__(self, func: Callable[[], V]) -> None
```

Key: `webcompy.signal._computed:Computed` · Exports: `from webcompy.signal import Computed`

Reactive value derived from a computation over other signals.

The computation function runs eagerly on construction and again whenever a signal it read during the last run changes. Reading `value` returns the cached result: recomputation is pull-based and skipped while all producers are unchanged.

**Args:**

- `func`: Zero-argument callable computing the derived value.

**Attributes:**

- `value`: The cached derived value, recomputed lazily when an upstream producer has changed.
- `last_clean_epoch`: Reactive-graph bookkeeping epoch in which this node was last brought up to date.

#### Members

**`producer_must_recompute`** (method)

```python
def producer_must_recompute(self) -> bool
```

Return `True` when the cached value must be recomputed.

**Returns:** `True` if the node is dirty, has never computed a value, or an upstream producer changed since the last computation.

**`producer_recompute_value`** (method)

```python
def producer_recompute_value(self) -> None
```

Recompute the derived value and bump the version on change.

**`value`** (property)

```python
@property
def value(self) -> V
```

Return the current derived value, recomputing when necessary.

**Returns:** The cached computation result.

### computed_property

```python
def computed_property(method: Callable[[Any], V]) -> Computed[V]
```

Key: `webcompy.signal._computed:computed_property` · Exports: `from webcompy.signal import computed_property`

Turn a method into a per-instance cached `Computed` property.

The wrapped method is evaluated lazily on first access; the result is cached per instance and recomputed only when the signals it read change.

**Args:**

- `method`: The method whose result is memoized.

**Returns:** A property exposing a per-instance `Computed[V]`.

### DictMutation

```python
class DictMutation:
    op: str
    key: str | int | None
    value: Any
```

Key: `webcompy.signal._dict:DictMutation` · Exports: `from webcompy.signal import DictMutation`

Record of the most recent mutating operation on a `ReactiveDict`.

**Args:**

- `op`: Operation name (e.g. `"set"`, `"delete"`, `"clear"`).
- `key`: Key the operation targeted, when applicable.
- `value`: Value set by the mutation, when applicable.

**Attributes:**

- `op`: Operation name (e.g. `"set"`, `"delete"`, `"clear"`).
- `key`: Key the operation targeted, when applicable.
- `value`: Value set by the mutation, when applicable.

### ListMutation

```python
class ListMutation:
    op: str
    index: int | None
    value: Any
```

Key: `webcompy.signal._list:ListMutation` · Exports: `from webcompy.signal import ListMutation`

Record of the most recent mutating operation on a `ReactiveList`.

**Args:**

- `op`: Operation name (e.g. `"append"`, `"pop"`, `"sort"`).
- `index`: Index the operation targeted, when applicable.
- `value`: Value involved in the mutation, when applicable.

**Attributes:**

- `op`: Operation name (e.g. `"append"`, `"pop"`, `"sort"`).
- `index`: Index the operation targeted, when applicable.
- `value`: Value involved in the mutation, when applicable.

### ReactiveDict

```python
class ReactiveDict(Signal[dict[K, V]]):
    def __init__(self, init_value: dict[K, V] | None = None) -> None
```

Key: `webcompy.signal._dict:ReactiveDict` · Exports: `from webcompy.signal import ReactiveDict`

Reactive wrapper around a `dict` behaving like `Signal[dict]`.

Mutation methods (`__setitem__`, `__delitem__`, `pop`, `clear`) propagate change notifications to consumers; read methods (`__getitem__`, `get`, `keys`, `values`, `items`, `__len__`, `__iter__`) record a read dependency. Each mutation stores a `DictMutation` describing it.

**Args:**

- `init_value`: Initial dictionary contents. Defaults to an empty dictionary.

#### Members

**`clear`** (method)

```python
def clear(self)
```

Remove all entries, notifying consumers.

**`get`** (method)

```python
def get(self, key: K, default: Any = None)
```

Return the value for `key`, recording a read dependency.

**Args:**

- `key`: Key to look up.
- `default`: Value returned when `key` is absent.

**Returns:** The mapped value or `default`.

**`items`** (method)

```python
def items(self)
```

Return the dictionary items, recording a read dependency.

**`keys`** (method)

```python
def keys(self)
```

Return the dictionary keys, recording a read dependency.

**`pop`** (method)

```python
def pop(self, key: K)
```

Remove `key` and return its value, notifying consumers.

**Args:**

- `key`: Key to remove.

**Returns:** The removed value.

**`values`** (method)

```python
def values(self)
```

Return the dictionary values, recording a read dependency.

### ReactiveList

```python
class ReactiveList(Signal[list[V]]):
    def __init__(self, init_value: list[V]) -> None
```

Key: `webcompy.signal._list:ReactiveList` · Exports: `from webcompy.signal import ReactiveList`

Reactive wrapper around a `list` behaving like `Signal[list]`.

Mutation methods (`append`, `extend`, `insert`, `pop`, `remove`, `sort`, `reverse`, `clear`, `__setitem__`) propagate change notifications to consumers; read methods (`__getitem__`, `__len__`, `__iter__`, `index`, `count`) record a read dependency. Each mutation stores a `ListMutation` describing it.

**Args:**

- `init_value`: Initial list contents.

#### Members

**`append`** (method)

```python
def append(self, value: V)
```

Append `value` to the end, notifying consumers.

**Args:**

- `value`: Item to append.

**`clear`** (method)

```python
def clear(self)
```

Remove all items, notifying consumers.

**`count`** (method)

```python
def count(self, value: V)
```

Return how many times `value` occurs, recording a read dependency.

**Args:**

- `value`: Item to count.

**Returns:** The number of occurrences.

**`extend`** (method)

```python
def extend(self, value: Iterable[V])
```

Extend the list with an iterable, notifying consumers.

**Args:**

- `value`: Iterable of items to append.

**`index`** (method)

```python
def index(self, value: V)
```

Return the position of `value`, recording a read dependency.

**Args:**

- `value`: Item to locate.

**Returns:** The zero-based index of the first match.

**`insert`** (method)

```python
def insert(self, index: int, value: V)
```

Insert `value` before `index`, notifying consumers.

**Args:**

- `index`: Position at which to insert.
- `value`: Item to insert.

**`pop`** (method)

```python
def pop(self, index: int | None = None)
```

Remove and return the item at `index`, notifying consumers.

**Args:**

- `index`: Position to remove; the last item when omitted.

**Returns:** The removed item.

**`remove`** (method)

```python
def remove(self, value: V)
```

Remove the first occurrence of `value`, notifying consumers.

**Args:**

- `value`: Item to remove.

**`reverse`** (method)

```python
def reverse(self)
```

Reverse the order of items in place, notifying consumers.

**`sort`** (method)

```python
def sort(self, key: Callable[[V], Any] = lambda it: it, reverse: bool = False)
```

Sort the list in place, notifying consumers.

**Args:**

- `key`: Key function applied to each item for comparison.
- `reverse`: Whether to sort in descending order.

### readonly

```python
def readonly(reactive: SignalBase[V]) -> ReadonlySignal[V]
```

Key: `webcompy.signal._readonly:readonly` · Exports: `from webcompy.signal import readonly`

Wrap `reactive` in a read-only view of its value.

**Args:**

- `reactive`: The signal to observe.

**Returns:** A `ReadonlySignal` mirroring the wrapped value reactively.

### ReadonlySignal

```python
class ReadonlySignal(Computed[V]):
    def __init__(self) -> None
```

Key: `webcompy.signal._readonly:ReadonlySignal` · Exports: `from webcompy.signal import ReadonlySignal`

Read-only reactive view over an underlying `SignalBase`.

Broadcasting the current value of the wrapped signal without exposing a write path. Instances are created via `readonly()` (internally `__create_instance__`); the constructor raises.

### Signal

```python
class Signal(SignalBase[V])
```

Key: `webcompy.signal._base:Signal` · Exports: `from webcompy.signal import Signal`

Mutable reactive value container.

`Signal` is the core state primitive. Assigning through the `value` setter or calling `set_value` stores a new value and notifies dependent `Computed` nodes, effects, and DOM bindings. Writes equal to the current value (under `==` or identity) are no-ops and do not propagate.

**Args:**

- `init_value`: Initial value of the signal.

**Attributes:**

- `value`: The current value; reading it records a read dependency and assigning it stores and propagates the new value.

#### Members

**`set_value`** (method)

```python
def set_value(self, new_value: V) -> V
```

Set the value, notifying consumers when it actually changes.

**Args:**

- `new_value`: The new value to store.

**Returns:** The stored value after the call.

**`value`** (property)

```python
@property
def value(self) -> V
```

Return the current value, recording a read dependency.

**Returns:** The current value.

### SignalBase

```python
class SignalBase(SignalNode, Generic[V]):
    def __init__(self, init_value: V) -> None
```

Key: `webcompy.signal._base:SignalBase` · Exports: `from webcompy.signal import SignalBase`

Base class of all reactive value containers.

A `SignalBase` holds a current value and participates in the reactive graph: reading `value` registers the active consumer as a dependent, and value changes notify registered consumers. Subclasses define how and when values change: `Signal` exposes user-facing mutation while `Computed` derives values from other signals.

**Args:**

- `init_value`: Initial value exposed by `value`.

**Attributes:**

- `value`: The current value; reading it registers the active consumer as a dependent of this node.

#### Members

**`on_after_updating`** (method)

```python
def on_after_updating(self, func: Callable[[V], Any]) -> CallbackConsumerNode
```

Register a callback that runs after each value change.

**Args:**

- `func`: Callback receiving the new value.

**Returns:** The callback consumer node created for the registration.

**`on_before_updating`** (method)

```python
def on_before_updating(self, func: Callable[[V], Any]) -> CallbackConsumerNode
```

Register a callback that runs before each value change.

**Args:**

- `func`: Callback receiving the previous value.

**Returns:** The callback consumer node created for the registration.

**`value`** (property)

```python
@property
def value(self) -> V
```

Return the current value, recording a read dependency.

**Returns:** The current value.

### use_computed

```python
def use_computed(factory: Callable[[], T]) -> Computed[T]
```

Key: `webcompy.signal._computed:use_computed` · Exports: `from webcompy import use_computed`, `from webcompy.signal import use_computed`

Create a reactive Computed value.

`use_computed()` accepts a zero-argument factory callable and returns a `Computed[T]`.  Computed values are not included in the SSR transfer payload and always recompute from their source signals on the client.

**Args:**

- `factory`: A zero-argument factory callable.

**Returns:** A `Computed[T]` whose value tracks the factory result.

**Raises:**

- `TypeError`: If `factory` is not callable.

### use_readonly_signal

```python
def use_readonly_signal(initial: T) -> tuple[ReadonlySignal[T], Callable[[T], T]]
```

Key: `webcompy.signal._readonly:use_readonly_signal` · Exports: `from webcompy import use_readonly_signal`, `from webcompy.signal import use_readonly_signal`

Create a read-only reactive value with an external update function.

`use_readonly_signal()` returns a `(ReadonlySignal[T], Callable[[T], T])` pair: the signal is readable reactively but exposes no setter, and the returned update function is the sole write path (it sets the value and returns the current value, deduplicating equal writes).  It is context-free — usable standalone or inside composables — and the value is never included in the SSR transfer payload.

**Args:**

- `initial`: The initial value of the signal.

**Returns:** A tuple of the read-only signal and its update function.

## Effects & Composables

### effect

```python
def effect(
    fn: Callable[[], Any],
    on_cleanup: Callable[[], Any] | None = None,
) -> EffectHandle
```

Key: `webcompy.signal._effect:effect` · Exports: `from webcompy.signal import effect`

Run `fn` and re-run it whenever a signal it read changes.

Dependencies are tracked dynamically: each run records the signals the function reads, and a change to any of them schedules the next run. A callable returned by `fn` is treated as a cleanup function invoked before the next run and on disposal.

**Args:**

- `fn`: The effect function. May return a cleanup callable.
- `on_cleanup`: Fallback cleanup callback used when `fn` returns a non-callable result.

**Returns:** A handle that can stop the effect via `dispose()`.

### EffectHandle

```python
class EffectHandle:
    def __init__(self, node: EffectNode) -> None
```

Key: `webcompy.signal._effect:EffectHandle` · Exports: `from webcompy.signal import EffectHandle`

Handle to a running effect, used to stop it.

#### Members

**`dispose`** (method)

```python
def dispose(self) -> None
```

Stop the effect permanently.

### EffectScope

```python
class EffectScope:
    def __init__(self) -> None
```

Key: `webcompy.signal._effect:EffectScope` · Exports: `from webcompy.signal import EffectScope`

Container that collects effects and disposes them together.

#### Members

**`dispose`** (method)

```python
def dispose(self) -> None
```

Dispose all effects collected in this scope.

### use_reactive_dict

```python
def use_reactive_dict(
    factory_or_key: str | Callable[[], dict[K, V]],
    maybe_factory: Callable[[], dict[K, V]] | None = None,
) -> ReactiveDict[K, V]
```

Key: `webcompy.signal._composable:use_reactive_dict` · Exports: `from webcompy import use_reactive_dict`, `from webcompy.signal import use_reactive_dict`

Create a transfer-capable ReactiveDict.

Same factory-skip semantics as `use_state()` but returns a `ReactiveDict[K, V]` with working mutation methods (`__setitem__`, `pop`, etc.).  Call inside a component setup function.

**Args:**

- `factory_or_key`: A zero-argument factory callable returning a dict, or an explicit string key when `maybe_factory` is also provided.
- `maybe_factory`: The zero-argument factory when the first argument is an explicit key.

**Returns:** A `ReactiveDict[K, V]` registered for SSR transfer when called inside component setup.

### use_reactive_list

```python
def use_reactive_list(
    factory_or_key: str | Callable[[], list[V]],
    maybe_factory: Callable[[], list[V]] | None = None,
) -> ReactiveList[V]
```

Key: `webcompy.signal._composable:use_reactive_list` · Exports: `from webcompy import use_reactive_list`, `from webcompy.signal import use_reactive_list`

Create a transfer-capable ReactiveList.

Same factory-skip semantics as `use_state()` but returns a `ReactiveList[V]` with working mutation methods (`append`, `pop`, etc.).  Call inside a component setup function.

**Args:**

- `factory_or_key`: A zero-argument factory callable returning a list, or an explicit string key when `maybe_factory` is also provided.
- `maybe_factory`: The zero-argument factory when the first argument is an explicit key.

**Returns:** A `ReactiveList[V]` registered for SSR transfer when called inside component setup.

### use_state

```python
def use_state(
    factory_or_key: str | Callable[[], T],
    maybe_factory: Callable[[], T] | None = None,
) -> Signal[T]
```

Key: `webcompy.signal._composable:use_state` · Exports: `from webcompy import use_state`, `from webcompy.signal import use_state`

Create a transfer-capable reactive Signal.

Call inside a component setup function. On the server the factory runs to produce the initial value; during browser hydration the factory is skipped and the value is restored from the SSR transfer payload.  Outside component setup a `UserWarning` is emitted and the signal is created without transfer registration.

**Args:**

- `factory_or_key`: A zero-argument factory callable, or an explicit string key when `maybe_factory` is also provided.
- `maybe_factory`: The zero-argument factory when the first argument is an explicit key.

**Returns:** A `Signal[T]` registered for SSR transfer when called inside component setup.

## Internal Reactivity Graph

### SignalNode

```python
class SignalNode:
    def __init__(self) -> None
```

Key: `webcompy.signal._graph:SignalNode` · Internal allowlist entry

Node of the reactive dependency graph.

Every reactive value is a node connected to the nodes it reads (producers) and the nodes that read it (consumers) via `SignalEdge` links. Framework code interacts with this base type to recompute consumers and propagate invalidation.

**Attributes:**

- `version`: Monotonic counter bumped whenever the value changes.
- `last_clean_epoch`: Epoch in which this node was last brought up to date.
- `dirty`: Whether the node's cached state is invalidated.
- `recomputing`: Whether a recomputation is currently in progress.
- `producers`: First incoming edge from a node this one read.
- `producers_tail`: Last incoming edge from a producer.
- `consumers`: First outgoing edge to a node that read this one.
- `consumers_tail`: Last outgoing edge to a consumer.
- `consumer_is_always_live`: Whether consumers are tracked continuously.

#### Members

**`producer_must_recompute`** (method)

```python
def producer_must_recompute(self) -> bool
```

Return `True` when this node's value is stale.

**Returns:** `True` if the node is dirty or was never computed.

**`producer_recompute_value`** (method)

```python
def producer_recompute_value(self) -> None
```

Recompute the value of this producer node.

**Raises:**

- `NotImplementedError`: Always; subclasses must provide the actual recomputation strategy.

<!-- generated:end -->

## Next steps

<!-- author:start:see-also -->
- Concept guides: [Reactive State](/documents/basic/reactive-state), [Read-only Signals and Events](/documents/advanced/readonly-signal), and [Signals and Streams](/documents/advanced/signal-stream).
- Hydration parity & live demo: [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer) and [ToDo List](/documents/examples/todo).
<!-- author:end:see-also -->
