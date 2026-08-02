## Context

The signal graph propagates mutations via a two-step sweep (`packages/webcompy/src/webcompy/signal/_graph.py`):

1. **`producer_notify_consumers(producer)`** — collects consumers into `consumers_to_notify` but ONLY those where `consumer.dirty` is `False`, then marks each collected consumer dirty and recurses via `consumer_mark_dirty`.
2. **`producer_update_value_version(producer)`** — brings a producer's value current for the epoch, early-returning when `_epoch == producer.last_clean_epoch`.

The current `producer_update_value_version` early-return does NOT clear `dirty`:

```python
def producer_update_value_version(producer: SignalNode) -> None:
    if _epoch == producer.last_clean_epoch:
        return                      # <-- BUG: stale dirty survives
    ...
```

In a diamond topology this strands a `Computed`. The sweep trace that reproduces the bug:

```
Topology:  A ──┐
              ├──▶ C ──▶ D
        B ──┘

epoch E starts (mutation → increment_epoch)
  notify A's consumers: C collected (C.dirty False) → C.dirty=True → recurse to D
  C is recomputed/cleaned for epoch E  (C.last_clean_epoch = E)
    BUT within the SAME sweep, B also notifies C
    B's notify run sees C.dirty is already True → C NOT re-collected (correct, no double-dispatch)
    However C.dirty remains True after the sweep
epoch E+1 (next mutation)
  notify A's consumers: C is skipped because C.dirty is still True
    → consumer_mark_dirty(C) never called → D never notified
    → D goes stale
```

The `feat-loop-metadata` design (decision D3) verified this experimentally and deferred it: *"This is a genuine framework bug worth a separate fix (clear `producer.dirty` on that early-return)."*

## Goals / Non-Goals

**Goals:**

- Eliminate the stuck-dirty strand so a `Computed` cleaned within an epoch and re-marked dirty mid-sweep remains reachable by the next mutation's notification sweep.
- Minimal, surgical change: one branch in `producer_update_value_version`.
- Regression coverage that fails before the fix and passes after.

**Non-Goals:**

- Redesigning `producer_notify_consumers`'s collection predicate (`if not consumer.dirty`). That skip is intentional — it prevents intra-sweep re-dispatch and duplicate notification. Only the residual-dirty symptom is fixed.
- Changing equality/laziness contracts.
- Addressing the separate browser async-scheduler interleave issue (deferred `RepeatElement._refresh` interleaving at `await` points), also noted in `feat-loop-metadata` D3.

## Decisions

### D1. Clear `producer.dirty` on the epoch early-return

The fix adds `producer.dirty = False` to the `_epoch == producer.last_clean_epoch` branch of `producer_update_value_version`:

```python
def producer_update_value_version(producer: SignalNode) -> None:
    if _epoch == producer.last_clean_epoch:
        producer.dirty = False       # <-- added: value is current for this epoch
        return
    ...
```

**Why this is safe.** `last_clean_epoch == _epoch` is an invariant meaning "this producer's value has already been made consistent with every mutation incorporated in the current epoch" — either by a successful `producer_recompute_value()` (which sets `last_clean_epoch = _epoch` at line 144) or by the not-dirty branch (line 137). Any `dirty = True` present at the early-return is therefore necessarily a stale residue from a mid-sweep re-mark, not a signal of an unincorporated mutation: a genuine new mutation always advances `_epoch` via `increment_epoch()` before notification, so it can never coincide with `last_clean_epoch == _epoch`. Clearing the flag restores the invariant the producer already satisfies and adds no recomputation.

**No double-dispatch risk.** `producer_notify_consumers` runs once per mutation sweep. Clearing `dirty` lets the NEXT epoch's sweep collect the node again (the desired behavior — the node SHOULD be notified for the new mutation). Within a single sweep the collection predicate already prevents re-dispatch, and clearing happens inside `producer_update_value_version` (a read-side poll), not inside the notify collection loop, so it cannot widen a single sweep's fan-out.

### D2. Rejected alternative — change the collection-time dirty skip

Modifying `producer_notify_consumers` to collect already-dirty consumers (e.g., always append, or re-check at dispatch) would change notification semantics: it would either re-dispatch within the same sweep (infinite loops / duplicate work) or require a separate "already-dispatched-this-epoch" marker, which is strictly more state than clearing one flag on the existing early-return. Rejected — it touches the hot notification path and risks the very intra-sweep re-dispatch the skip is designed to prevent.

### D3. Rejected alternative — bump `last_clean_epoch` only via explicit `producer_mark_clean`

Routing all dirty-clearing through `producer_mark_clean` (and having the early-return call it) is functionally equivalent to D1 but couples the read-side poll to the dedicated clean API and obscures the intent. D1's inline clear is the minimal, readable expression of the invariant. Rejected for clarity, not correctness.

## Risks / Trade-offs

- [A node legitimately awaiting recompute in the same epoch could be wrongly cleared] → Cannot happen: a pending recompute is gated by `producer_must_recompute()` in the SECOND branch (line 136), which only runs when `_epoch != last_clean_epoch`. The early-return branch is reached exclusively when the value is already current.
- [Subtle interaction with `consumer_poll_producers_for_change`] → That function calls `producer_update_value_version` to refresh a producer before deciding whether the consumer changed; clearing dirty there is consistent (the producer is fresh for the epoch) and does not affect the version-comparison return value.
- [Hidden reliance on stale dirty elsewhere] → No code path treats a stale dirty on a same-epoch-clean node as meaningful; `producer_must_recompute` returns `dirty or value is _SENTINEL`, but the early-return precedes that check, so behavior is unchanged for any node not on the early-return path.

## Migration Plan

None. The change restores the intended invariant; no API or behavior migration is required. Downstream code that happened to depend on the buggy stale-dirty residue (none known) would simply receive the notifications it should have been receiving all along.

## Open Questions

None.
