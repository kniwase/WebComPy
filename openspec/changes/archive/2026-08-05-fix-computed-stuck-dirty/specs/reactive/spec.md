## ADDED Requirements

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
