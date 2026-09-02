---
title: Typed Realtime
description: Send and receive dataclass-typed WebSocket messages with use_websocket — metadata-typed fields, strict reconstruction, skip-on-error handling, and custom type registration.
---

# Typed Realtime

Raw WebSocket messages are text frames; realtime applications almost always exchange structured messages. Pass a dataclass to `use_websocket` as `message_type` and the handle becomes an `AsyncIterator[T]` whose `.send()` accepts `T` instances — metadata-typed fields (`datetime`, `UUID`, `Decimal`, `Enum`, registered custom types) round-trip with full type fidelity on top of the same shared connection, reconnection, and lifecycle behavior as the raw handle.

## Typed messages

```python
from dataclasses import dataclass
from webcompy.realtime import use_websocket

@dataclass
class ChatMessage:
    user: str
    text: str

ws = use_websocket("/api/chat", message_type=ChatMessage)

async for message in ws:
    print(message.user, message.text)  # dataclass instances, not strings

ws.send(ChatMessage(user="ada", text="hi"))  # sends one JSON text frame
```

`message_type` must be a dataclass; any other target raises a descriptive `TypeError` at call time. Without `message_type` (the default) the handle behaves exactly like the raw text handle. All other parameters (`protocols`, reconnection settings, `buffer_while_disconnected`, `.state`, `.last_close`, `.close()`, connection sharing) are unchanged — typing is a codec layer over the transport.

## The wire envelope

Each frame is a single JSON object: the payload fields plus a `__webcompy_transfer_meta__` member that records metadata-typed fields by JSON Pointer path (the typed-response body wire mode):

```json
{
  "user": "ada",
  "text": "hi",
  "sent_at": "2026-08-05T12:34:56",
  "__webcompy_transfer_meta__": {"/sent_at": "datetime"}
}
```

On send, metadata-typed fields are encoded and tagged automatically. On receive, the member is split off, validated, and applied before schema-driven reconstruction:

```python
@dataclass
class Event:
    name: str
    at: datetime

ws = use_websocket("/api/events", message_type=Event)
async for event in ws:
    print(event.at)  # a datetime instance, never a string
```

A frame without the meta member is still reconstructed schema-driven (ISO-8601 strings for `datetime`/`date`/`time`/`UUID` are coerced by the annotations alone).

## Strict reconstruction

Reconstruction is strict by default: a frame with unknown extra fields or missing required fields is **skipped** (see [Error handling](#error-handling)). This catches schema drift loudly at the boundary — realtime peers are usually deployed together. If a peer is allowed to be forward-compatible with your schema, opt into lenient coercion:

```python
ws = use_websocket("/api/chat", message_type=ChatMessage, strict=False)
```

With `strict=False`, unknown fields are ignored and values are coerced leniently. Type-tag validation is strict regardless of this parameter: a frame referencing a type tag outside the closed builtin set and your registered custom types is always skipped, and a tag is **never** resolved to a class by name.

## Error handling

A frame that fails JSON parsing, type-tag validation, or schema reconstruction is skipped — it is never yielded, the subscription and the underlying connection survive, and subsequent valid frames are delivered normally. The failure is surfaced on `.last_error: Signal[Exception | None]` and a warning is logged. A subsequent successful frame resets `.last_error` to `None`.

Only these three categories are treated as malformed frames. A genuine programming error in the decode path — for example a custom decoder raising an unrelated exception — is not swallowed: it propagates to the consumer so it cannot hide behind `.last_error`.

Render an error badge from the signal so failures are visible instead of silent:

```python
from webcompy.signal import use_computed, use_state

error_text = use_computed(lambda: "" if ws.last_error.value is None else str(ws.last_error.value))
```

Because one malformed message must not tear down every consumer of a shared connection, the error never kills the stream — but an unobserved `.last_error` can hide a poison frame, so keep the badge or monitor the signal.

## Custom types

Register encoder/decoder pairs for your own types within the app DI scope; qualified-name tags follow the json-rpc allowlist pattern and the registry is app-scoped (no module-level globals, no cross-app leakage). Builtin tags (`datetime`, `date`, `time`, `set`, `frozenset`, `bytes`, `decimal`, `tuple`, `path`, `uuid`) always work without registration.

```python
from decimal import Decimal
from webcompy.realtime import register_realtime_type_handler

@dataclass
class Money:
    amount: str

def encode_money(money: Money) -> str:
    return money.amount

def decode_money(value: str) -> Money:
    return Money(amount=value)

@dataclass
class Payment:
    user: str
    money: Money

with app.di_scope():
    register_realtime_type_handler(Money, encode_money, decode_money)

ws = use_websocket("/api/payments", message_type=Payment)
async for payment in ws:
    print(payment.money)  # a Money instance
```

Calling `register_realtime_type_handler` outside an app DI scope emits a `UserWarning` and is a no-op; without a registry, decoding accepts only builtin tags.

## Notes and limits

- **Dataclass targets only** — the body wire mode requires a top-level JSON object; wrap collections and scalars in a dataclass.
- **No hydration transfer** — typed messages, `.last_error`, and registrations never enter the SSR/SSG hydration payload; outside the browser the typed handle behaves like the raw handle's empty closed fallback.
- **No replay** — reconnection does not replay missed typed messages; re-pull authoritative state when `.state` returns to `OPEN` (see the raw WebSocket [gap/refetch recipe](/documents/advanced/websocket#the-gaprefetch-recipe)).
