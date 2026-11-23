---
title: Typed Realtime
description: Send and receive dataclass-typed WebSocket messages with use_websocket(message_type=...) — metadata-typed fields, strict reconstruction, error signals, and custom allowlisted codecs.
---

# Typed Realtime

Passing `message_type=YourDataclass` to `use_websocket()` turns raw text frames into validated Python objects. You send `YourDataclass` instances with `ws.send(msg)` and iterate typed `YourDataclass` values from `async for msg in ws:`, including metadata-typed fields (`datetime`, `UUID`, `Decimal`, `Enum`, `bytes`) and custom codecs registered on both sides.

## When to use

- **Exchanging structured messages over a plain WebSocket endpoint** — pass `message_type=` to `use_websocket()`.
- **Passing raw strings or binary-free custom protocols** — use plain [WebSocket](/documents/advanced/websocket).
- **Want typed procedures, batching, streaming generators, or cursor-replayed subscriptions** — use [RPC Contracts](/documents/advanced/rpc-contracts) and [RPC over WebSocket](/documents/advanced/rpc-websocket).

## Setup

Define a `@dataclass` message schema in a shared module and pass it as `message_type=` to `use_websocket()`. The returned handle is a `TypedWebSocketHandle[T]`:

```python
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from webcompy.components import ComponentContext, define_component, on_mounted
from webcompy.elements import html, repeat
from webcompy.realtime import use_websocket
from webcompy.signal import use_reactive_list


@dataclass
class ChatMessage:
    id: UUID
    user: str
    text: str
    sent_at: datetime


@define_component()
def TypedChat(context: ComponentContext[None]):
    ws = use_websocket("/api/chat", message_type=ChatMessage)
    messages = use_reactive_list(lambda: [])

    @on_mounted
    async def receive():
        async for msg in ws:
            messages.append(msg)

    return html.UL(
        {},
        repeat(
            messages,
            lambda m: html.LI({}, f"[{m.sent_at:%H:%M}] {m.user}: {m.text}"),
        ),
    )
```

## Recipes

### Inspect decode failures via `.last_error`

Malformed frames (invalid JSON, schema mismatches, or rejected metadata tags) never crash the receive loop or close the socket. Instead, WebComPy skips the bad frame, logs a warning, and stores the exception on `ws.last_error` (`Signal[Exception | None]`):

```python
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.realtime import use_websocket


@define_component()
def MonitoredFeed(context: ComponentContext[None]):
    ws = use_websocket("/api/events", message_type=ChatMessage)

    return html.P(
        {},
        use_computed(
            lambda: f"Last frame error: {ws.last_error.value}"
            if ws.last_error.value is not None
            else "All frames valid"
        ),
    )
```

### Allow extra server fields with `strict=False`

By default (`strict=True`), unexpected extra fields or missing required fields reject the incoming frame. Set `strict=False` when deploying additive server schema updates ahead of browser clients:

```python
ws = use_websocket("/api/chat", message_type=ChatMessage, strict=False)
```

### Register custom types on both client and server

Built-in codecs handle standard JSON types plus `datetime`, `date`, `time`, `timedelta`, `UUID`, `Decimal`, `bytes`, `set`, `frozenset`, `tuple`, `re.Pattern`, `Enum`, and nested dataclasses. To send domain value objects such as `Money`, call `register_realtime_type_handler(cls, encoder, decoder)` inside an active app DI scope on **both** client setup and server handling:

```python
from dataclasses import dataclass

from webcompy.components import ComponentContext, define_component
from webcompy.realtime import register_realtime_type_handler, use_websocket


@dataclass(frozen=True)
class Money:
    cents: int
    currency: str


def register_domain_codecs() -> None:
    register_realtime_type_handler(
        Money,
        encoder=lambda m: {"cents": m.cents, "currency": m.currency},
        decoder=lambda d: Money(cents=d["cents"], currency=d["currency"]),
    )


@dataclass
class PaymentEvent:
    order_id: str
    amount: Money


@define_component()
def PaymentTicker(context: ComponentContext[None]):
    register_domain_codecs()
    ws = use_websocket("/api/payments", message_type=PaymentEvent)
    ...
```

Type tags use qualified class names and are strictly allowlisted: only built-in tags and tags explicitly registered via `register_realtime_type_handler()` are decoded.

## Behavior notes

- **Wire envelope format**: Sending an instance serializes its dataclass fields into a JSON object alongside the `__webcompy_transfer_meta__` member mapping field paths to registered type tags. Incoming frames strip `__webcompy_transfer_meta__`, apply metadata decoders strictly against the allowlist, and reconstruct `message_type` via `from_json(..., strict=strict)`.
- **Skip-on-error recovery**: When a frame raises `ValueError` or `TypeError` during JSON parsing, metadata validation, or schema reconstruction, `ws.last_error.value` captures the error, a warning is emitted, and the iterator skips directly to the next frame without tearing down the shared socket. A subsequent valid frame resets `ws.last_error.value` back to `None`.
- **Inherited transport semantics**: Sharing by `(url, protocols)`, reconnection backoff, `.state`, `.last_close`, `buffer_while_disconnected`, component-destroy cleanup, and SSR/SSG no-op degradation work identically to plain `use_websocket()` (returning a `TypedWebSocketHandle[T]` whose `.send()` warns and discards and whose iterator ends immediately outside the browser).
- **Allowlist security**: WebComPy never dynamically imports classes named inside incoming frames; unregistered metadata tags fail frame decoding and land on `.last_error`.

## Pitfalls

- **Registering on only one side**: If the browser encodes a `Money` field with `register_realtime_type_handler()` but the server does not (or vice versa), the receiving side rejects the metadata tag as unregistered. Keep dataclass models and codec registration in a shared package imported by both server and client.
- **Calling `register_realtime_type_handler()` outside an app DI scope**: Calling it at bare module import time before a render/app DI scope exists emits a `UserWarning` and becomes a no-op.
- **Expecting missed-message replay on reconnect**: Like raw WebSockets, typed handles do not replay frames dropped while offline. Refetch authoritative state when `.state` returns to `OPEN` using the [gap/refetch recipe](/documents/advanced/websocket#the-gaprefetch-recipe).
- **Passing a non-dataclass `message_type`**: Supplying `dict`, a plain class, or `str` raises `TypeError` — `message_type` must be a `@dataclass` type.

## Next steps

- Review connection sharing, backoff math, and gap recovery in [WebSocket](/documents/advanced/websocket).
- Move up to declarative server/client contracts in [RPC Contracts](/documents/advanced/rpc-contracts).
- Get built-in cursor replay on reconnect in [RPC over WebSocket](/documents/advanced/rpc-websocket).
- Collect typed events into reactive lists in [Signals and Streams](/documents/advanced/signal-stream).
