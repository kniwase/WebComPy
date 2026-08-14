## Context

`docs_app/components/navigation.py` `Navbar` manages dropdown menus. Today:

- `_menu_positions: dict[int, Signal[tuple[float, float]]]` — lazy per-menu signals holding measured dropdown positions, written only from event handlers (`_toggle`, `_measure_open_menus`), read via `use_computed` in the dropdown style.
- Manual listeners: `dom.add_document_event_listener("scroll", ...)`, `host.add_window_event_listener("resize", ...)`, `dom.add_document_event_listener("click", ...)` with a manual `on_before_destroy` cleanup, plus optional `HOST_PORT_KEY` injection.
- `_open_states: dict[int, Signal[bool]]` and `_mobile_open = use_state(False)` are click-driven interaction state.

The framework provides `use_readonly_signal(initial)` (read-only value + sole update channel, context-free, no hydration transfer) and `use_window_event` / `use_document_event` (state-event bridges with automatic `on_before_destroy` cleanup, transform mapping, and error containment) — readonly-signal spec.

## Goals / Non-Goals

**Goals:**
- Express measured menu positions as a single read-only snapshot signal whose only write path is the update function.
- Replace the scroll/resize manual listeners with `use_document_event` / `use_window_event`, removing manual attach/cleanup boilerplate.
- Preserve observable behavior: menus still re-measure on every scroll/resize event; click-outside still closes menus on every outside click.

**Non-Goals:**
- Changing click-driven state (`_open_states`, `_mobile_open`) — stays `Signal[bool]` / `use_state`.
- Introducing new framework composables or port changes.
- Changing the click-outside listener (occurrence semantics, stays manual).

## Decisions

### Decision 1: One canonical snapshot signal instead of per-menu signals

Use a single `positions, update_positions = use_readonly_signal({})` holding `dict[int, tuple[float, float]]`, instead of the lazy dict of per-menu `Signal` pairs.

Rationale: `use_document_event` / `use_window_event` bridge exactly one event to exactly one signal value. The measured state is naturally "the set of current positions", and a snapshot dict gives the composables a real value to hold, with structural-equality dedup suppressing notifications when nothing moved.

Alternatives considered:
- **Per-menu `use_readonly_signal` pairs kept in the lazy dict**: rejected — the event composables' transforms would have to write several per-menu pairs as a side effect while returning a dummy value for their own signal, leaving the composable signal as dead weight.
- **Two mirrors (scroll-derived and resize-derived snapshots) consumed directly**: rejected — `_toggle` writes only one of them, so after a resize the other is stale; keeping both in sync spreads the write path across two signals.

### Decision 2: Transform re-measures, updates the canonical snapshot, and returns it

```python
def _measure(_ev) -> dict[int, tuple[float, float]]:
    snap = _measure_open_menus()   # returns the snapshot of open menus
    update_positions(snap)         # canonical write
    return snap                    # keeps the composable mirror in sync

_, _ = use_document_event("scroll", {}, transform=_measure)
_, _ = use_window_event("resize", {}, transform=_measure)
```

The event composables' own signals act as mirrors holding the same snapshot; the template reads the canonical `positions` signal only. Because the composable's handler always runs the transform and only deduplicates the resulting `update(value)` call, re-measurement still happens on every scroll/resize event, while notification (and thus re-render) is deduplicated when the snapshot did not change.

`_toggle` measures immediately after opening a menu and calls `update_positions(...)` directly — the click cannot wait for a scroll/resize event.

### Decision 3: Click-outside stays manual

The outside-click listener is an occurrence event (every outside click must close all menus; equality-dedup would drop repeated events). It remains a manual `add_document_event_listener` with its own `on_before_destroy` cleanup. Destroy-hook ordering matters: register the manual `on_before_destroy` cleanup **before** calling the event composables, so the composables' chained cleanup is appended after it and is not overwritten.

### Decision 4: SSR/hydration behavior

During SSR/SSG the server ports are no-ops, so the snapshot stays `{}` and the template reads `positions.value.get(idx, (0.0, 0.0))` — the same defaults as today. `use_readonly_signal` never participates in hydration transfer (positions are transient client measurements), which also keeps the payload unchanged.

## Risks / Trade-offs

- [Snapshot dedup changes re-render granularity] → Previously each per-menu position signal notified its own consumers; now any position change re-evaluates all dropdown style computeds that read the snapshot. The docs navbar has a handful of dropdowns, so the cost is negligible.
- [Transform has a side effect on the canonical signal] → Contained and documented: the transform is invoked on every event by the composable contract, and errors are logged/swallowed by the composable, so a failed measurement cannot break event dispatch.
- [Manual click-outside cleanup ordering] → Mitigated by registering the manual cleanup before the composable calls (Decision 3); verified by E2E dropdown tests.
