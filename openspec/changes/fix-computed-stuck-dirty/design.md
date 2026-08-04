## Context

The signal graph propagates mutations via a two-step sweep (`packages/webcompy/src/webcompy/signal/_graph.py`):

1. **`producer_notify_consumers(producer)`** — collects consumers into `consumers_to_notify` but ONLY those where `consumer.dirty` is `False`, then marks each collected consumer dirty and recurses via `consumer_mark_dirty`.
2. **`producer_update_value_version(producer)`** — brings a producer's value current for the epoch, early-returning when `_epoch == producer.last_clean_epoch`.

The original `producer_update_value_version` early-return does NOT clear `dirty`:

```python
def producer_update_value_version(producer: SignalNode) -> None:
    if _epoch == producer.last_clean_epoch:
        return                      # <-- BUG: stale dirty survives
    ...
```

In a diamond topology this strands a `Computed`. The sweep trace that reproduces the bug:

```
Topology:  A (source) ─▶ B ─┐
                            ├──▶ D (Computed) ──▶ consumer callback
           A ────────────▶ C ┘

epoch E begins (mutation on A → increment_epoch)
  producer_notify_consumers(A) collects [B, C] up front (both dirty=False)
  loop marks B: B.dirty=True → consumer_mark_dirty(B) → D.dirty=True → D's callback dispatches
    → callback reads D.value → producer_update_value_version(D) → D recomputes for E
    → D reads B.value (B recomputed, clean for E) and C.value
    → C is eagerly recomputed and cleaned for E (last_clean_epoch = E, dirty = False)
  the collection loop (which re-checks `if not consumer.dirty` at mark time) reaches C:
    C.dirty is False again → C is re-marked dirty = True
    → consumer_mark_dirty(C) → D: not dirty → D.dirty=True → D's callback dispatches
    → callback reads D.value → producer_update_value_version(D)
    → _epoch == D.last_clean_epoch (D was cleaned earlier in this sweep)
    → EARLY RETURN without clearing dirty   ← D stays dirty=True
epoch E+1 (next mutation)
  notify A's consumers: B marked → consumer_mark_dirty(B) → notify B's consumers
  D is skipped (D.dirty is still True) → consumer_mark_dirty(D) never called
    → D's callback never dispatched → D goes stale
```

The re-mark is NOT a second sweep: `producer_notify_consumers` collects all non-dirty
consumers up front, and any consumer that a mid-sweep dispatch eagerly recomputed clean
is marked again when the loop reaches it. A node with two producers (diamond) makes this
easy to hit — an eager read through one producer path cleans a node that a second
collected path later re-marks — but the residue (clean value + stale `dirty = True` for
the epoch) is the same with a single producer.

**Nested-chain variant (found during review of the original one-line fix).** Clearing
`dirty` on the early-return only repairs nodes whose value is actually re-read. In a
nested chain (`source → left/right → inner → outer → callback`), the second producer
path re-marks `inner` and the second branch dirty, and the re-dispatched callback
short-circuits on its version check (`CallbackConsumerNode._dispatch`:
`producer.version <= old_version → return`) WITHOUT re-reading them. Their values remain
clean for the epoch but their `dirty` flags stay set. The next mutation's sweep skips
`inner` (dirty) and `outer` never receives the notification — observable stale UI
(reproduced: a `TextElement` bound to `outer` stops updating after the first mutation).

The `feat-loop-metadata` design (decision D3) verified this experimentally and deferred it: *"This is a genuine framework bug worth a separate fix (clear `producer.dirty` on that early-return)."*

## Goals / Non-Goals

**Goals:**

- Eliminate the stuck-dirty strand so a `Computed` cleaned within an epoch and re-marked dirty mid-sweep remains reachable by the next mutation's notification sweep — including mid-chain nodes in nested topologies that are never re-read after the re-mark.
- Minimal, surgical change confined to the notification sweep; no recomputation and no new node state.
- Regression coverage that fails before the fix and passes after (graph unit, computed callback, DOM).

**Non-Goals:**

- Redesigning `producer_notify_consumers`'s collection predicate (`if not consumer.dirty`). That skip is unchanged and intentional — it prevents intra-sweep re-collection and duplicate notification. Only the mark step gains an epoch guard.
- Adding per-node state (e.g., a `last_notified_epoch` marker). The existing `last_clean_epoch` already encodes "value current for this epoch".
- Performing recomputation or recursive upstream polling inside the sweep — `Computed` laziness is preserved.
- Changing equality/laziness contracts.
- Addressing the separate browser async-scheduler interleave issue (deferred `RepeatElement._refresh` interleaving at `await` points), also noted in `feat-loop-metadata` D3.

## Decisions

### D1. Epoch-aware mark-time gate in `producer_notify_consumers`

The primary fix: when the collection loop reaches a consumer whose `last_clean_epoch`
equals the current `_epoch`, that consumer's value already incorporates every mutation
of this sweep (it was recomputed or marked clean for this epoch during an earlier
dispatch). Re-marking it would dispatch a duplicate same-epoch notification and, in
nested chains, leave it stuck-dirty because the duplicate dispatch's version check
short-circuits before re-reading it. The mark step therefore clears any residual
`dirty` and skips the re-mark — but it does NOT drop the notification for the node's
own consumers. It propagates via `consumer_mark_dirty` (which does not set the skipped
node's own `dirty`), so consumers that depend only on the skipped node still receive
the sweep's updates:

```python
def producer_notify_consumers(producer: SignalNode) -> None:
    _set_in_notification_phase(True)
    try:
        consumers_to_notify: list[SignalNode] = []
        edge = producer.consumers
        while edge is not None:
            consumer = edge.consumer
            if not consumer.dirty:
                consumers_to_notify.append(consumer)
            edge = edge.next_consumer
        for consumer in consumers_to_notify:
            if consumer.last_clean_epoch == _epoch:
                consumer.dirty = False
                consumer_mark_dirty(consumer)
                continue
            if not consumer.dirty:
                consumer.dirty = True
                consumer_mark_dirty(consumer)
    finally:
        _set_in_notification_phase(False)
```

**Why this is safe.** `last_clean_epoch == _epoch` is an invariant meaning "this
consumer's value has already been made consistent with every mutation incorporated in
the current epoch" — either by a successful recompute (`producer_recompute_value()`
sets `last_clean_epoch = _epoch`) or by the not-dirty branch. A genuine new mutation
always advances `_epoch` via `increment_epoch()` before notification, so a
same-epoch-clean consumer can never have unincorporated changes. Skipping the re-mark
reintroduces no staleness and adds no recomputation.

**Why the gate is at mark time, not collection time.** Collection happens up front,
before any dispatch; the cleanup that makes a node same-epoch-clean happens DURING an
earlier dispatch in the same loop. Only the mark step observes the post-dispatch state.

**Why the gate propagates instead of returning.** A skipped node may have changed
during the sweep (its eager recompute bumped its version), so its consumers' read edges
are stale. Consumers that were already brought current this sweep (e.g. the diamond's
first-path chain) are skipped in turn by the recursive gate — no duplicate dispatch.
Consumers not yet current (e.g. a side consumer that depends only on the skipped node)
are marked and dispatched exactly once, and read the skipped node's already-current
value. Without the propagation, such side consumers would silently miss every
notification: a `Computed` used both inside a diamond and bound directly to the DOM
would freeze permanently. The propagation adds no recomputation and no node state; it
only walks consumer edges of the skipped node, bounded by the same DAG recursion the
mark path already uses.

**No double-dispatch risk.** `producer_notify_consumers` runs once per mutation sweep.
The gate prevents the second producer path from re-marking an already-clean node, so
the duplicate dispatch that previously fired (and was only suppressed for callbacks by
the version check) never happens at all — for `CallbackConsumerNode`, `Computed`
consumers, and `EffectNode` alike. A same-epoch-clean `CallbackConsumerNode` reached by
the propagation (possible only when registered mid-sweep, since `last_clean_epoch` is
not updated by dispatch) is dispatched but its version check short-circuits, preserving
batch semantics.

**Node created mid-sweep.** A consumer registered during a sweep has
`last_clean_epoch == _epoch` at creation; the gate skips it for the current mutation,
which is consistent with batch semantics (subscriptions created after a change do not
receive the notification for that change).

### D2. Keep the `producer_update_value_version` early-return clear as a defensive invariant

The original one-line fix (`producer.dirty = False` on the `_epoch == last_clean_epoch`
early return) remains: a node directly polled on the early-return path is never left
with a stale flag, and the clear is a no-op for nodes that are already clean. With D1
in place no mid-chain node reaches the next epoch stuck-dirty, but the clear keeps the
read-side poll self-healing for any residual residue and preserves the invariant for
the directly-polled node.

**Why the clear-only fix was insufficient (superseded as the primary fix).** It
repairs only the node being read. Mid-chain nodes re-marked by the second producer path
are never re-read (the version-check short-circuit), so they stay stuck-dirty and
strand the next sweep regardless of the clear. The nested-chain reproduction confirms:
with only the clear, a `TextElement` bound to the outer `Computed` stops updating after
the first mutation.

### D3. Rejected alternative — recursive upstream polling / clearing

Having `producer_update_value_version` (or the sweep) recursively traverse and clear
upstream producers would repair the nested case but adds graph traversal to the read
path, risks eager recomputation of nodes that were legitimately dirty for a new
mutation, and interacts badly with dynamic-dependency re-tracking
(`consumer_after_computation` prunes edges mid-recompute). Rejected: D1 is preventive
(downstream-only propagation, no reads, no upstream traversal) and addresses the root
cause — the re-mark itself.

### D4. Rejected alternative — change the collection-time dirty skip / add a `last_notified_epoch` marker

Collecting already-dirty consumers (e.g., always append, or re-check at dispatch)
would either re-dispatch within the same sweep (infinite loops / duplicate work) or
require a separate "already-dispatched-this-epoch" marker — strictly more state than
reusing the existing `last_clean_epoch`. Rejected: it touches the hot notification path
and risks the very intra-sweep re-dispatch the skip is designed to prevent.

## Risks / Trade-offs

- [A node legitimately awaiting recompute in the same epoch could be wrongly skipped] → Cannot happen: a pending recompute is gated by `producer_must_recompute()` in the value-version path, which only runs when `_epoch != last_clean_epoch`. The gate fires exclusively for values already current for the epoch.
- [Consumers of a skipped node could miss the notification] → Cannot happen: the gate propagates to the skipped node's consumers; consumers not yet current for the epoch are marked and dispatched exactly once, and read the already-current value. Only consumers already current (whose dispatch would be a duplicate) are skipped in turn.
- [Subtle interaction with `consumer_poll_producers_for_change`] → That function calls `producer_update_value_version` to refresh a producer before deciding whether the consumer changed; clearing dirty there is consistent (the producer is fresh for the epoch) and does not affect the version-comparison return value.
- [Hidden reliance on stale dirty elsewhere] → No code path treats a stale dirty on a same-epoch-clean node as meaningful; `producer_must_recompute` returns `dirty or value is _SENTINEL`, but a same-epoch-clean node is never passed to the recompute gate in a way that depends on the residue.
- [Behavior change for tests that call `producer_notify_consumers` directly without `increment_epoch()`] → Production call sites (`Signal.set_value`, `_change_event`) always increment the epoch before notifying; the existing direct-notify unit tests were updated to follow the same discipline.

## Migration Plan

None. The change restores the intended invariant; no API or behavior migration is required. Downstream code that happened to depend on the buggy stale-dirty residue (none known) would simply receive the notifications it should have been receiving all along.

## Open Questions

None.
