## ADDED Requirements

### Requirement: Computed SHALL notify every callback consumer whose last-notified value changed after recompute

A `Computed` with multiple `on_after_updating` consumers SHALL dispatch each consumer's callback when the recomputed value differs from that consumer's last-notified value — including the 2nd and subsequent consumers whose `_dispatch` runs after the `Computed` was already recomputed by an earlier consumer within the same mutation epoch. A consumer SHALL NOT be silently dropped because the producer's version did not advance during its own dispatch (the epoch-skip path). A consumer SHALL NOT be dispatched when the recomputed value is equal (`is` or `==`) to its last-notified value, regardless of producer version bumps caused by subscription.

#### Scenario: Multiple consumers of one Computed all receive a changed value
- **WHEN** a `Computed` has two `on_after_updating` consumers and its source signal mutates so the recomputed value changes
- **THEN** BOTH consumers' callbacks SHALL fire with the new value, even though only the first consumer's dispatch recomputed the `Computed` (the second dispatch hits the per-epoch recompute skip)

#### Scenario: Equal recomputed value does not dispatch any consumer
- **WHEN** a `Computed`'s source mutates but the recomputed value equals the previous value
- **THEN** NO consumer's callback SHALL fire

### Requirement: A detached callback consumer SHALL NOT be dispatched during an in-flight notification sweep

Notification sweeps SHALL snapshot `SignalEdge` objects (not bare consumers) when collecting callbacks, mark an edge inactive as soon as it is detached from the graph, and skip inactive edges before marking or dispatching. If a callback destroys another consumer (via `consumer_destroy`) while a sweep is in progress, the destroyed consumer SHALL NOT fire — even though its edge was still linked when the sweep's snapshot was taken. This SHALL apply to `on_after_updating` dispatch (`producer_notify_consumers`) and to `on_before_updating` notification (`_notify_before_callbacks`) alike.

#### Scenario: A callback destroys a later consumer during dispatch
- **WHEN** two consumers are registered on one `Computed`, and the first-dispatched consumer's callback calls `consumer_destroy` on the second
- **THEN** the second consumer's callback SHALL NOT fire for that mutation

#### Scenario: A before-update callback destroys a later before-update consumer
- **WHEN** two `on_before_updating` consumers are registered on a `Signal`, and the first-notified consumer's callback destroys the second
- **THEN** the second consumer's callback SHALL NOT fire for that mutation

### Requirement: Registering an after-update callback on a dirty Computed SHALL use the current value as the baseline

`on_after_updating` registration on a `Computed` SHALL establish the producer's current logical value as the node's baseline before the live-consumer edge is added: a `Computed` that is dirty (a source mutated without any read since) SHALL be brought current via the value-version path at registration time. Registration SHALL NOT invoke the callback and SHALL NOT create graph edges as a side effect. With the baseline current, a later mutation whose recomputed value equals the registration-time value SHALL NOT fire the callback, and a mutation whose recomputed value differs (including a return to the value the `Computed` had before the dirtying mutation) SHALL fire it.

#### Scenario: Registering on a dirty Computed does not false-fire on an equal result
- **WHEN** `a` mutates so `Computed(lambda: abs(a.value))` becomes dirty (cached value still old), then a callback is registered and `a` mutates again such that `abs(a.value)` equals the value at registration
- **THEN** the callback SHALL NOT fire (the registration-time value is the baseline, not the stale cached value)

#### Scenario: Registering on a dirty Computed fires on return to the initial value
- **WHEN** `a` mutates so `Computed(lambda: a.value)` becomes dirty, then a callback is registered and `a` returns to the value it had before the dirtying mutation
- **THEN** the callback SHALL fire (the recomputed value differs from the registration-time baseline)
