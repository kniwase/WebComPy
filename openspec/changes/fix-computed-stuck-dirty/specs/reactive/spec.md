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
