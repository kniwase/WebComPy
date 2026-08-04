## Why

In a diamond signal topology, a `Computed` that is cleaned within the current epoch and then re-marked dirty later in the same notification sweep is left with `dirty = True`. `producer_notify_consumers()` collects all non-dirty consumers up front, so a consumer that a mid-sweep dispatch eagerly recomputed clean is marked again when the collection loop reaches it — and a diamond's second producer path makes such mid-sweep eager recomputes easy to trigger. `producer_update_value_version()` early-returns on `_epoch == last_clean_epoch` WITHOUT clearing the stale dirty flag, so the next mutation's `producer_notify_consumers()` skips the node (it only collects consumers where `dirty` is `False`). Downstream consumers stop receiving updates, producing stale UI.

The stale-dirty residue is not limited to the node whose value is re-read: in a nested chain (`source → left/right → inner → outer → callback`), the mid-sweep re-mark marks `inner` and the second branch dirty, and the re-dispatched callback short-circuits on its version check WITHOUT re-reading them. Their values stay clean for the epoch but their `dirty` flags stay set, so the next mutation's sweep skips `inner` and `outer` never receives the notification — the UI silently freezes (reproduced: a `TextElement` bound to `outer` stops updating after the first mutation).

## What Changes

- Add an **epoch-aware mark-time gate** to `producer_notify_consumers()` in `packages/webcompy/src/webcompy/signal/_graph.py`: when the collection loop reaches a consumer whose `last_clean_epoch` equals the current `_epoch`, its value already incorporates the mutation that started this sweep — clear any residual `dirty`, do NOT re-mark it, but DO propagate to its own consumers via `consumer_mark_dirty` (itself gate-checked at every level) so consumers that depend only on the skipped node still receive exactly one notification. This prevents the second producer path from re-marking already-clean nodes, so no mid-chain node is left stuck-dirty, no duplicate same-epoch notification is synthesized, and no consumer of a cleaned node is silently dropped.
- Keep the existing `producer_update_value_version()` early-return dirty clear as a defensive invariant: a node directly polled on the early-return path is never left with a stale flag.
- Add regression coverage: nested-diamond graph unit tests (including a side consumer of the cleaned node), nested-diamond `Computed` callback integration tests (chain and side consumer), and a `TextElement` DOM test that all fail before the gate and pass after.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `reactive`: adds requirements stating that (a) a `Computed` cleaned within the current epoch SHALL NOT be excluded from a subsequent notification sweep, and (b) the notification sweep SHALL NOT re-mark a consumer already clean for the current epoch, formalizing the epoch-aware gate the mark step must honor.

## Impact

- **Affected code**: `packages/webcompy/src/webcompy/signal/_graph.py` (mark-time epoch gate with consumer propagation in `producer_notify_consumers`; the existing early-return clear in `producer_update_value_version` is retained).
- **Tests**: `tests/test_graph.py` (epoch-gate unit test incl. side-consumer propagation; existing direct-notify tests updated to advance the epoch first, matching production call order); `tests/test_signal.py` (nested-diamond callback tests, chain and side consumer); `tests/test_elements_browser.py` (`TextElement` DOM test).
- **APIs/dependencies**: none — internal signal-graph behavior only; no public API change.
- **Risk**: very low. The gate only skips consumers whose values are already current for the sweep's epoch and propagates to their consumers; it performs no recomputation, adds no state, and preserves single-dispatch semantics.

## Known Issues Addressed

Resolves the stuck-dirty signal-graph bug that the `feat-loop-metadata` design (`openspec/changes/archive/2026-08-02-feat-loop-metadata/design.md`, decision D3) identified, verified experimentally, and explicitly deferred: *"This is a genuine framework bug worth a separate fix (clear `producer.dirty` on that early-return)."* It also resolves the nested-chain variant (mid-chain nodes left stuck-dirty because the version-check short-circuit never re-reads them) found during review of this change.

## Non-goals

- Redesigning the notification/propagation algorithm or the `producer_notify_consumers` collection predicate (`if not consumer.dirty` is unchanged — it still prevents intra-sweep re-collection; only the mark step gains the epoch gate).
- Adding new per-node state (e.g., a `last_notified_epoch` marker) — the existing `last_clean_epoch` already encodes "current for this epoch".
- Performing any recomputation or recursive upstream polling during the sweep — `Computed` laziness is preserved.
- Changing the signal equality contract (`old is new or old == new`) or `Computed` laziness semantics.
- Addressing the separate browser async-scheduler interleave issue (deferred `RepeatElement._refresh` interleaving) also noted in `feat-loop-metadata` D3; that remains out of scope.
- Re-evaluating the shared per-loop `positions` `Computed` design rejected in `feat-loop-metadata` D3; while this fix removes one of the obstacles, the browser async interleave problem still blocks it.
