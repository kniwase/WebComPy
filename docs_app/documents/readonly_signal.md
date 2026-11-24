---
title: Read-only Signals and Events
description: Expose reactive state to consumers without letting them mutate it — use_readonly_signal, use_window_event, use_document_event, lifecycle chaining, and SSR behavior.
---

# Read-only Signals and Events

`use_readonly_signal()` gives you a signal whose value is readable by components and computed derivations, but writable only through an explicit internal callback. Built on top of it, `use_window_event()` and `use_document_event()` turn browser state changes such as viewport size, network status, and page visibility into clean read-only signals.

## When to use

- **Need consumer-writable component or app state** — use [`use_state`](/documents/basic/reactive-state) (or `Signal`) when consumers may assign `.value` directly.
- **Want to broadcast state owned by a service or browser API** — use `use_readonly_signal`, `use_window_event`, or `use_document_event` so UI code can read reactively without mutating the source.
- **Consuming an ordered feed where duplicate values still matter** — use [Signals and Streams](/documents/advanced/signal-stream) instead, because signals collapse consecutive equal writes.

## Setup

Call `use_readonly_signal(initial)` to create a `(view, update)` pair. `view` is a `ReadonlySignal[T]` exposing `.value` (readable anywhere, including `@use_computed`), while `update` is a private callable that sets the next value and returns it:

```python
from webcompy import use_computed, use_readonly_signal
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.signal import ReadonlySignal


@define_component()
def StatusBanner(context: ComponentContext[None]):
    online, set_online = use_readonly_signal(True)
    status_label = use_computed(lambda: "Online" if online.value else "Offline")

    return html.DIV(
        {},
        html.SPAN({}, status_label),
        html.BUTTON({"@click": lambda _ev: set_online(not online.value)}, "Toggle"),
    )
```

`view` has no `.value =` setter — assigning to `online.value` raises `AttributeError`. When annotating helper signatures, import `ReadonlySignal` from `webcompy.signal`.

## Recipes

### Track window events with `use_window_event()`

Use `use_window_event(event_type, initial, transform=...)` inside component setup to mirror a `window` property into a read-only signal and automatically remove the listener when the component is destroyed:

```python
from webcompy import use_computed, use_window_event
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component()
def ViewportIndicator(context: ComponentContext[None]):
    width, _set_width = use_window_event(
        "resize",
        1024,
        transform=lambda ev: int(ev.target.innerWidth),
    )
    layout = use_computed(lambda: "mobile" if width.value < 768 else "desktop")

    return html.P({}, use_computed(lambda: f"{width.value}px ({layout.value})"))
```

### Track document state with `use_document_event()`

`use_document_event(event_type, initial, transform=...)` attaches a document-level listener using the same contract. Returning the update callback lets you also react programmatically or override initial state in tests:

```python
from webcompy import use_computed, use_document_event
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component()
def VisibilityBadge(context: ComponentContext[None]):
    visibility, _ = use_document_event(
        "visibilitychange",
        "visible",
        transform=lambda ev: str(ev.target.visibilityState),
    )

    return html.SPAN({}, use_computed(lambda: f"Tab: {visibility.value}"))
```

### Share module-level external state without a component context

`use_readonly_signal()` has no context requirement. Call it at module scope or inside a service class and export only the read-only view (or a `ReadonlySignal` factory) to components:

```python
from webcompy import use_readonly_signal
from webcompy.signal import ReadonlySignal

auth_user, _set_auth_user = use_readonly_signal[str | None](None)


def on_session_changed(username: str | None) -> None:
    _set_auth_user(username)


def current_user() -> ReadonlySignal[str | None]:
    return auth_user
```

If an external service needs direct DOM or timer callbacks that start outside component setup, pair `use_readonly_signal()` with your service's own start/stop methods and trigger updates via `set_value`.

## Behavior notes

- **Deduplication**: `ReadonlySignal` wraps an internal `Signal` and inherits its equality check. Writing a value equal to the current `.value` skips downstream notifications.
- **Chained cleanup hooks**: Both `use_window_event()` and `use_document_event()` register their listener teardown via chained destroy hooks, so calling multiple event composables (or defining your own `on_before_destroy` handler) in the same component runs every cleanup function on destroy without overwriting earlier ones.
- **Resilient transforms**: If `transform(event)` raises an exception, WebComPy logs a warning and leaves the signal at its previous value rather than crashing the browser event dispatch loop.
- **SSR and hydration**: During server rendering and static generation (`webcompy generate`), `use_window_event()` and `use_document_event()` detect the no-op server port, attach no listeners, and leave the signal at `initial`. Neither `use_readonly_signal()` nor the DOM event composables transfer state into `<script id="__webcompy_data__">`; listeners attach only once the browser boots.

## Pitfalls

- **Silently dropped duplicates**: Using `use_readonly_signal` for an event log where repeated identical messages (e.g. `"ping"`, `"ping"`) must each trigger work will lose every repeat after the first. Use [Signals and Streams](/documents/advanced/signal-stream) (`to_reactive_list`) for occurrence streams.
- **In-place mutation of mutable values**: Mutating a list or dict inside `update(current)` keeps the same identity or equality reference and can bypass updates. Always pass a fresh object to `update(...)`.
- **Calling DOM event composables outside setup**: Calling `use_window_event()` or `use_document_event()` at module import time or inside an event handler outside component setup emits a `UserWarning` and returns `(view, update)` with no DOM listener attached.

## Next steps

- Convert between occurrence streams and signals in [Signals and Streams](/documents/advanced/signal-stream).
- Revisit writable component state and `Computed` derivations in [Reactive State](/documents/basic/reactive-state).
- Compare read-only DOM event signals with DI-managed cookie locale state in [Internationalization](/documents/advanced/i18n).
- Handle inline element event handlers (`@click`, `@input`) in [Elements & Events](/documents/basic/elements-and-events).
