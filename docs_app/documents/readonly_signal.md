---
title: Read-only Signals and Events
description: Hold externally-produced state as a read-only signal with use_readonly_signal, use_window_event, and use_document_event.
---

# Read-only Signals and Events

WebComPy's state primitives are **cells**: they hold *current state* and propagate changes, with an equality contract that suppresses same-value writes. When the state comes from outside your component — a window resize, a visibility change, a callback from non-WebComPy code — you want a value your UI can read reactively, but you do not want to hand out write access. `use_readonly_signal` gives you exactly that: a read-only signal whose **only** write path is the `update` function it returns.

This page covers the primitive and the two convenience composables for browser state events. If your data is a stream of *occurrences* (chat messages, ticks, WebSocket events) where every arrival matters, see [Signals and Streams](/documents/signal-stream) instead — signal equality would silently drop duplicates.

## use_readonly_signal: an external-only write path

```python
from webcompy import use_readonly_signal

view, update = use_readonly_signal(0)
# view: ReadonlySignal[int] — readable, but has no setter
# update(...) is the ONLY way to change it
```

- The returned signal is a `ReadonlySignal` (`from webcompy.signal import ReadonlySignal` for annotations): it exposes `.value` and nothing else — no `set_value`, no value setter.
- `update` mirrors the signal equality contract: passing a value equal to the current one does not notify consumers (a resized width that did not change stays silent).
- It is **context-free**: call it in a standalone script, at module level, or inside another composable — no component setup required, no warning emitted.
- Values are client-side derived state: they never participate in hydration transfer, and SSR renders `initial` unchanged.

Bridging an external callback:

```python
from webcompy import use_readonly_signal

view, update = use_readonly_signal(0)

def on_pressure(value):
    update(value)

pressure_sensor.subscribe(on_pressure)
```

## use_window_event: window state events

`use_window_event(event_type, initial, *, transform=None)` bridges a window-level state event into a read-only signal. Call it inside a component's setup: the listener is attached immediately and **automatically removed when the component is destroyed** — no orphaned listener or browser proxy.

```python
from webcompy import use_window_event

@define_component
def Page(context):
    width, _ = use_window_event("resize", 0, transform=lambda e: e.target.innerWidth)
    return html.DIV({}, str(width.value))
```

- `transform: Callable[[Any], T] | None` converts the raw event into the signal's value type; when omitted, the raw event object is stored as-is.
- An exception raised inside `transform` is logged and swallowed — the signal keeps its previous value and the browser's event dispatch is not interrupted.
- Inside component setup with a resolvable `HostPort`, the listener is registered and unregistered on `on_before_destroy`. The composable occupies the component's single destroy-hook slot, so register your own `on_before_destroy` hook **before** calling it — a hook registered later would overwrite the cleanup and leak the listener.
- Outside component setup a `UserWarning` is emitted and **nothing is attached** (leak-free). During SSR/SSG the server port is a no-op, so the page renders `initial` and hydration is unaffected.

## use_document_event: document state events

`use_document_event` is the same composable for document-level events (e.g. `visibilitychange`, pointer state), registered through `DOMPort.add_document_event_listener`:

```python
from webcompy import use_document_event

@define_component
def Page(context):
    hidden, _ = use_document_event(
        "visibilitychange",
        False,
        transform=lambda e: bool(e.target.hidden),
    )
    return html.DIV({}, "hidden" if hidden.value else "visible")
```

Lifecycle and error semantics are identical to `use_window_event`.

## State events, not occurrence events

Signal equality means `update(v)` where `v` equals the current value produces **no notification**. That is exactly right for state: the window did not change size, the tab did not change visibility. It is wrong for occurrence streams — a duplicate message or a repeated tick would be silently swallowed. For those, use `to_reactive_list` (accumulate every item) or `to_async_iter` (consume every update) from `webcompy.aio`, or a plain callable event handler.

## Standalone usage

The composables deliberately refuse to attach listeners outside component setup. If you need a window/document listener at module level or in a script, register it yourself and pair it with the primitive:

```python
from webcompy import use_readonly_signal

view, update = use_readonly_signal(0)

def on_resize(event):
    update(event.target.innerWidth)

# browser-only setup; remove the listener yourself
host = ...  # your HostPort (e.g. via inject(HOST_PORT_KEY) inside an app scope)
_remove = host.add_window_event_listener("resize", on_resize)
```
