## Why

The docs_app `Navbar` component manages dropdown menu positions with writable `Signal` instances that are only ever written by event handlers, and it registers document/window listeners (scroll, resize, click-outside) with manual attach/cleanup boilerplate. The framework's `use_readonly_signal` / `use_window_event` / `use_document_event` composables (readonly-signal spec) provide exactly this shape: externally-produced state with a single update channel, plus lifecycle-managed event bridging. The Navbar should adopt them — removing manual listener cleanup and expressing the event-derived state with the read-only contract it was designed for.

## What Changes

- **MODIFIED** `docs_app/components/navigation.py`:
  - Per-menu position `Signal[tuple[float, float]]` instances are replaced by a single canonical read-only snapshot signal created with `use_readonly_signal({})`, holding `dict[int, tuple[float, float]]` of measured dropdown positions.
  - The scroll and resize listeners are replaced by `use_document_event("scroll", ...)` and `use_window_event("resize", ...)`; their `transform` re-measures the open menus, updates the canonical snapshot through its update function, and returns the snapshot to keep the composable signal in sync. Equal snapshots are deduplicated by signal equality (no spurious notifications when nothing moved).
  - The `_toggle` click handler measures immediately after opening and writes through the same update function.
  - The click-outside listener remains a manual `add_document_event_listener` with `on_before_destroy` cleanup: it is an occurrence event (every outside click must close menus) and must not be bridged through state-event composables.
  - The manual `inject(DOM_PORT_KEY)` / `inject(HOST_PORT_KEY)` wiring for scroll/resize is removed; the composables resolve ports themselves.
- No framework code changes; this is an adoption of existing public composables in the docs application.

## Capabilities

### New Capabilities

(none — no new framework capability is introduced)

### Modified Capabilities

- `docs-site-documents`: adds a requirement documenting the Navbar dropdown state-management contract (read-only snapshot positions driven by `use_document_event` / `use_window_event`, immediate measurement on toggle, manual occurrence-based outside-click handling).

## Known Issues Addressed

- **Manual window/document listener management in docs_app Navbar**: scroll/resize listeners are currently attached and removed by hand (`on_before_destroy` cleanup plus optional `HOST_PORT_KEY` injection). Moving them to `use_document_event` / `use_window_event` delegates lifecycle cleanup to the composables, following the Event Handler Leaks invariant (readonly-signal spec).

## Non-goals

- Changing the behavior of the dropdown menus, the click-outside handling, or the `_open_states` / `_mobile_open` click-driven state (they stay `Signal[bool]` / `use_state`).
- Introducing new framework composables (e.g., scroll-position or media-query helpers) — those are a separate framework change.
- Touching the framework's event/signal implementation.

## Impact

- **Affected**: `docs_app/components/navigation.py` only.
- **Behavior**: No observable change — menu open/close, positioning, and re-measurement on scroll/resize behave as before (re-measurement still runs on every event; only notifications are deduplicated by snapshot equality).
- **Verification**: `uv run python -m webcompy generate` (SSG), `ruff` / `pyright`, and the `docs-home` E2E group (`e2e/docs/test_home.py` dropdown tests).
