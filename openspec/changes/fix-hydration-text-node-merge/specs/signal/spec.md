## ADDED Requirements

### Requirement: Computed SHALL notify every callback consumer whose last-notified value changed after recompute

A `Computed` with multiple `on_after_updating` consumers SHALL dispatch each consumer's callback when the recomputed value differs from that consumer's last-notified value — including the 2nd and subsequent consumers whose `_dispatch` runs after the `Computed` was already recomputed by an earlier consumer within the same mutation epoch. A consumer SHALL NOT be silently dropped because the producer's version did not advance during its own dispatch (the epoch-skip path). A consumer SHALL NOT be dispatched when the recomputed value is equal (`is` or `==`) to its last-notified value, regardless of producer version bumps caused by subscription.

#### Scenario: Multiple consumers of one Computed all receive a changed value
- **WHEN** a `Computed` has two `on_after_updating` consumers and its source signal mutates so the recomputed value changes
- **THEN** BOTH consumers' callbacks SHALL fire with the new value, even though only the first consumer's dispatch recomputed the `Computed` (the second dispatch hits the per-epoch recompute skip)

#### Scenario: Equal recomputed value does not dispatch any consumer
- **WHEN** a `Computed`'s source mutates but the recomputed value equals the previous value
- **THEN** NO consumer's callback SHALL fire
