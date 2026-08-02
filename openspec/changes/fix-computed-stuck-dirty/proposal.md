## Why

In a diamond signal topology, a `Computed` that is cleaned within the current epoch and then re-marked dirty by a second producer during the same notification sweep is left with `dirty = True`. `producer_update_value_version()` early-returns on `_epoch == last_clean_epoch` WITHOUT clearing the stale dirty flag, so the next mutation's `producer_notify_consumers()` skips the node (it only collects consumers where `dirty` is `False`). Downstream consumers stop receiving updates, producing stale UI. This is a genuine framework bug that the `feat-loop-metadata` design (decision D3) isolated and deferred for a dedicated fix.

## What Changes

- Fix `producer_update_value_version()` in `packages/webcompy/src/webcompy/signal/_graph.py` so the `_epoch == last_clean_epoch` early-return clears the producer's stale `dirty` flag. Because that condition means "the producer's value has already been brought current for this epoch", any residual `dirty` is erroneous and must not survive the call.
- Add a diamond-topology regression test in `tests/test_graph.py` that reproduces the mid-sweep re-mark + epoch early-return scenario and asserts the downstream consumer is notified on the subsequent mutation.
- Add an integration test covering a `Computed`-driven DOM/text update across two mutations to guard against silent stale updates.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `reactive`: adds a requirement stating that a `Computed` cleaned within the current epoch SHALL NOT be excluded from a subsequent notification sweep, formalizing the dirty-clearing invariant that the early-return branch must honor.

## Impact

- **Affected code**: `packages/webcompy/src/webcompy/signal/_graph.py` (single-branch one-line behavior change in `producer_update_value_version`).
- **Tests**: `tests/test_graph.py` (new scenario in `TestDiamondTopology`); a new or existing signal integration test.
- **APIs/dependencies**: none — internal signal-graph behavior only; no public API change.
- **Risk**: very low. The cleared flag reflects an invariant the producer already satisfied (its value is current for the epoch); no recomputation is suppressed and no extra notification is synthesized within the same sweep.

## Known Issues Addressed

Resolves the stuck-dirty signal-graph bug that the `feat-loop-metadata` design (`openspec/changes/archive/2026-08-02-feat-loop-metadata/design.md`, decision D3) identified, verified experimentally, and explicitly deferred: *"This is a genuine framework bug worth a separate fix (clear `producer.dirty` on that early-return)."*

## Non-goals

- Redesigning the notification/propagation algorithm or the `producer_notify_consumers` collection strategy (the `if not consumer.dirty` skip is intentional and prevents intra-sweep re-dispatch; only the residual-dirty symptom is fixed).
- Changing the signal equality contract (`old is new or old == new`) or `Computed` laziness semantics.
- Addressing the separate browser async-scheduler interleave issue (deferred `RepeatElement._refresh` interleaving) also noted in `feat-loop-metadata` D3; that remains out of scope.
- Re-evaluating the shared per-loop `positions` `Computed` design rejected in `feat-loop-metadata` D3; while this fix removes one of the obstacles, the browser async interleave problem still blocks it.
