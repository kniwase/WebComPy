## Why

WebComPy has no way to hold externally-produced state (window/document events, callbacks from non-WebComPy code) as a read-only reactive value. `to_signal` requires a pull-based iterable and exposes a publicly writable `Signal`, and `readonly()` only wraps an existing writable signal. Consumers of external state today either leak write access, re-implement browser listener and proxy lifecycle by hand, or wrap events into async queues. There is no primitive that gives a ReadonlySignal whose value can only change through an external function call.

## What Changes

- Add `use_readonly_signal(initial)` returning a `(ReadonlySignal[T], update: Callable[[T], None])` tuple. The update function is the only write path; the returned signal type guarantees read-only access. Context-free: works outside component setup (standalone) and inside composable implementations. No hydration transfer.
- Add a new `webcompy.events` package with state-event composables built on the readonly primitive:
  - `use_window_event(event_type, initial, *, transform=identity)` bridged via `HostPort.add_window_event_listener`
  - `use_document_event(event_type, initial, *, transform=identity)` bridged via `DOMPort.add_document_event_listener`
  - Called inside component setup, the listener is attached and automatically unsubscribed on `on_before_destroy`. Called outside component setup (including SSR/SSG and missing DI scope), the composable emits a `UserWarning` and attaches nothing (no listener leak).
- Export `use_readonly_signal`, `use_window_event`, and `use_document_event` from the `webcompy` top-level package (alongside the existing `use_state`, `use_local_storage`, and friends).
- Add test-support: the fake ports in `webcompy-testing` gain the ability to record and trigger window/document event listeners so the helpers are testable headlessly.

## Capabilities

### New Capabilities

- `readonly-signal`: A context-free primitive for constructing a read-only signal with an external-only update channel, plus window/document state-event composables that bridge `HostPort`/`DOMPort` event sources into `ReadonlySignal` values with component-lifecycle cleanup.

### Modified Capabilities

- None. Existing specs (`reactive`, `composables`, `signal-stream`, `port-abstraction`) keep their requirements unchanged; the new capability layers on top without altering behavior.

## Impact

- Code: `packages/webcompy/src/webcompy/signal/_readonly.py` gains `use_readonly_signal`; a new `packages/webcompy/src/webcompy/events/` package is introduced; `packages/webcompy/src/webcompy/__init__.py` exports the new composables.
- Ports: `HostPort.add_window_event_listener` and `DOMPort.add_document_event_listener` are reused as-is (no API change).
- Testing: `packages/webcompy-testing` fake ports need listener recording/triggering support; new unit tests for the primitive and the helpers.
- Docs: a docs_app page for the capability; `AGENTS.md` "Current Specs" list and File→Spec Mapping table updated; `scripts/check-doc-spec-refs.py` regression must pass.
- Dependencies: none.

## Non-goals

- Occurrence-type events (click, keypress, ticks) are NOT bridged to signals: signal equality semantics would silently drop duplicate occurrences, and plain callable event handlers are the appropriate tool. The bridging targets state-like events only.
- A node/element-level event composable (`use_node_event`) is NOT added. Existing declarative element `events={}` handlers plus `:bind` already cover element events, and pairing them with `use_readonly_signal` is a one-line composition.
- No error/finished channel is added (unlike `StreamResult`): a read-only state signal has no async pipeline, and transform errors are logged and swallowed rather than surfaced.
- No hydration transfer of readonly state is introduced.
- `to_signal`/`to_reactive_list`/`to_async_iter` (signal-stream) are unchanged.

## Known Issues Addressed

- None directly. The change is designed to be consistent with the Event Handler Leaks invariant: the primitive attaches nothing, and the helpers attach a listener only when a lifecycle cleanup path exists (inside component setup), so no orphaned window/document listener or proxy can accumulate.