# Readonly-Signal

## Purpose

Provide a read-only reactive value whose only write path is an external function call, plus browser state-event composables that convert window/document event sources into such read-only signals. The primitive is context-free (usable standalone and inside composable implementations), carries no hydration transfer, and its DOM wrappers attach listeners only when a component-lifecycle cleanup path exists — so no window/document listener can leak. It complements `signal-stream` (pull-based iterable bridging with writable Signal output) by covering push-based *state* sources with a genuinely read-only public type.

## ADDED Requirements

### Requirement: use_readonly_signal shall construct a read-only signal with an external-only update channel

The framework SHALL provide `use_readonly_signal(initial)` returning `(ReadonlySignal[T], update)` where:

- `initial: T` is the value assigned to the read-only signal at construction (a callable value is treated as a plain value, never as a factory);
- the first tuple element is a `ReadonlySignal[T]` (via `readonly()`) exposing only `.value` — no setter, no `set_value`;
- `update: Callable[[T], T]` is the SOLE write path and SHALL be the private `Signal.set_value` bound method: it returns the current value after the write (the newly assigned value, or the unchanged current value when the equality check suppressed the write); assigning through `update` mirrors the signal equality contract: an item equal to the current value SHALL NOT notify consumers (state-event semantics, by design — occurrence-type events must not be bridged this way);
- the returned `ReadonlySignal` SHALL always reflect the value last passed to `update`, initialized to `initial`.

`use_readonly_signal` SHALL be context-free: it works without an active component setup context (standalone scripts, helper functions, other composables) and SHALL NOT emit a `UserWarning` when called outside component setup. It SHALL NOT register any transfer entry and SHALL NOT require lifecycle cleanup (it attaches nothing external).

#### Scenario: Initial value is readable immediately

- **WHEN** a caller writes `view, update = use_readonly_signal(10)`
- **THEN** `view.value` SHALL be `10` before `update` is ever called

#### Scenario: update is the only write path

- **WHEN** `update(42)` is called
- **THEN** `view.value` SHALL become `42`
- **AND** reactive consumers of `view` SHALL be notified of the change

#### Scenario: update returns the current value

- **WHEN** `update(42)` is called on a signal whose value becomes `42`
- **THEN** the return value SHALL be `42`
- **AND** calling `update(42)` again SHALL return `42` (the current value) without notifying consumers

#### Scenario: Equal consecutive updates are not re-notified

- **WHEN** the signal value is `5` and `update(5)` is called
- **THEN** `view.value` SHALL remain `5` (the assignment is idempotent)
- **AND** consumers SHALL NOT be notified, consistent with the signal equality contract

#### Scenario: ReadonlySignal exposes no write access

- **WHEN** a consumer attempts `view.value = 0` or `view.set_value(0)` on the returned `ReadonlySignal`
- **THEN** the write SHALL fail (the `ReadonlySignal` public type has no value setter or `set_value` method)

#### Scenario: Standalone usage outside component setup

- **WHEN** `use_readonly_signal(0)` is called in a standalone script or inside another composable's implementation
- **THEN** a working `(ReadonlySignal, update)` pair SHALL be returned
- **AND** no `UserWarning` SHALL be emitted

### Requirement: use_readonly_signal shall not participate in hydration transfer

Values created by `use_readonly_signal` are client-side derived state and SHALL NOT be collected into the hydration transfer payload (same rule as `Computed` and the `signal-stream` bridges). During SSR/SSG the signal SHALL render its `initial` value; the browser SHALL keep `initial` until `update` is called.

#### Scenario: SSG output contains no readonly state

- **WHEN** a page using `use_readonly_signal` is statically generated
- **THEN** the hydration payload SHALL NOT contain the read-only signal's value

### Requirement: use_window_event shall bridge window state events into a read-only signal

The framework SHALL provide `use_window_event(event_type, initial, *, transform=None)` importable from `webcompy` and `webcompy.events`, returning `(ReadonlySignal[T], update)` via the `use_readonly_signal` primitive. `transform` SHALL be typed `Callable[[Any], T] | None`; when `None`, the raw event object is passed through to `update` unchanged (identity). When the caller is inside an active component setup context and a `HostPort` is available in the DI scope, the composable SHALL:

- obtain a cleanup-returning listener handle via `HostPort.add_window_event_listener(event_type, handler)`;
- wire `handler` so each firing maps the raw event through `transform` (identity when `transform` is `None`) and passes the result to `update`;
- register the returned unsubscribe on the component's `on_before_destroy` lifecycle (chained with any existing hook, following the storage composables pattern) so the listener and its browser proxy are removed when the component is destroyed.

When called outside an active component setup context (including non-deterministic standalone browser code), the composable SHALL emit a `UserWarning` and SHALL NOT attach any listener (leak-free). When no `HostPort` resolves in the DI scope, the composable SHALL NOT attach a listener; on the server the `ServerHostPort` is used and its window listener is a no-op, so SSR/SSG simply render `initial` unchanged. Exceptions raised inside `transform` while handling an event SHALL be caught, logged via `webcompy.logging.warning`, and swallowed — they SHALL NOT propagate into the event dispatch.

Signal equality applies: a transformed value equal to the current value SHALL NOT notify consumers (e.g. a deduplicated width on resize).

#### Scenario: Resize events update the signal through a transform

- **WHEN** a component calls `use_window_event("resize", 0, transform=lambda e: e.target.innerWidth)` and a `resize` event with a new width fires
- **THEN** the first tuple element's `.value` SHALL become the transformed width
- **AND** reactive consumers of the signal SHALL be notified

#### Scenario: Repeating width produces no notification

- **WHEN** a second `resize` event transforms to the same value as the current signal value
- **THEN** `view.value` SHALL stay the same and consumers SHALL NOT be notified

#### Scenario: Component destroy removes the listener

- **WHEN** the owning component is destroyed
- **THEN** the `HostPort` listener SHALL be unsubscribed (the cleanup returned by `add_window_event_listener` SHALL be invoked) and no further events SHALL update the signal

#### Scenario: Called outside component setup attaches nothing

- **WHEN** `use_window_event` is called with no active component setup context
- **THEN** a `UserWarning` SHALL be emitted
- **AND** no listener SHALL be attached (no leak)
- **AND** the returned signal SHALL stay at `initial`

#### Scenario: Transform error is contained

- **WHEN** a fired event causes `transform` to raise
- **THEN** a warning SHALL be logged
- **AND** the signal SHALL remain unchanged
- **AND** the exception SHALL NOT propagate out of the event handler

### Requirement: use_document_event shall bridge document state events into a read-only signal

The framework SHALL provide `use_document_event(event_type, initial, *, transform=None)` importable from `webcompy` and `webcompy.events`, with the same `(ReadonlySignal[T], update)` return shape and lifecycle semantics as `use_window_event` — including the `Callable[[Any], T] | None` transform contract (identity when `None`) — except the listener SHALL be registered through `DOMPort.add_document_event_listener(event_type, handler)`. Outside an active component setup context a `UserWarning` SHALL be emitted and no listener SHALL be attached; missing `DOMPort` resolution or server rendering SHALL attach nothing and keep the signal at `initial`; `transform` exceptions SHALL be logged and swallowed.

#### Scenario: Document-level event updates the signal

- **WHEN** a component calls `use_document_event("visibilitychange", "visible", transform=...)` and a matching document event fires
- **THEN** the signal SHALL update to the transformed value with normal reactivity

#### Scenario: Component destroy removes the document listener

- **WHEN** the owning component is destroyed
- **THEN** the `DOMPort` listener SHALL be unsubscribed and no further document events SHALL update the signal

### Requirement: Event source composables shall attach listeners only with lifecycle cleanup

`use_window_event` and `use_document_event` SHALL follow the Event Handler Leaks invariant: a listener SHALL be attached only when the composable can guarantee removal — i.e. an active component setup context exists to hook `on_before_destroy`. The returned cleanup from the port SHALL be invoked exactly once on component destroy. No module-level registries SHALL be introduced (No-New-Globals invariant).

#### Scenario: Listener registration pairs with a single guaranteed removal

- **WHEN** a component uses `use_window_event` and is destroyed after many re-renders
- **THEN** exactly one unsubscribe SHALL run, removing the listener and destroying its browser proxy, and no duplicate listeners SHALL accumulate across re-renders of the same component

#### Scenario: Async setup failure still runs the registered cleanup

- **WHEN** an async component setup body registers a `use_window_event` listener and the async body subsequently raises or is cancelled
- **THEN** the component's destruction path SHALL invoke the destroy hooks registered inside the async body — including the listener unsubscribe — so the listener and its browser proxy SHALL NOT leak
- **AND** the component SHALL be removed from its parent without re-running the failed setup

### Requirement: Readonly-signal composables shall be importable from the webcompy top-level package

`use_readonly_signal` SHALL be importable from `webcompy` and from `webcompy.signal`; `use_window_event` and `use_document_event` SHALL be importable from `webcompy` and from `webcompy.events`. The top-level `webcompy` imports the project's `use_*` composable family, following the precedent set by `use_state`, `use_local_storage`, and `use_session_storage`. `ReadonlySignal` SHALL be importable from `webcompy.signal` as a public type for annotations (e.g. `view: ReadonlySignal[int] = ...`); it SHALL NOT be re-exported from the `webcompy` top-level package (matching the `Computed` precedent).

#### Scenario: Top-level imports resolve

- **WHEN** a developer writes `from webcompy import use_readonly_signal, use_window_event, use_document_event`
- **THEN** all three imports SHALL succeed and be callable

#### Scenario: Feature-package imports resolve

- **WHEN** a developer writes `from webcompy.signal import use_readonly_signal` and `from webcompy.events import use_window_event, use_document_event`
- **THEN** the imports SHALL succeed and refer to the same objects as the top-level imports

#### Scenario: ReadonlySignal is usable as a type annotation

- **WHEN** a developer writes `view: ReadonlySignal[int]` with `from webcompy.signal import ReadonlySignal`
- **THEN** the import SHALL succeed and the annotation SHALL be valid
- **AND** `ReadonlySignal` SHALL NOT be importable from the `webcompy` top-level package