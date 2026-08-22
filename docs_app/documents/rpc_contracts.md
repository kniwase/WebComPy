---
title: RPC Contracts
description: Declarative RPC contracts for typed HTTP and WebSocket calls — Procedure, StreamingProcedure, Subscription, RpcCall, batch, notify, and the schema-module convention.
---

# RPC Contracts

Declarative, statically typed RPC contracts shared between server and browser. Define `Procedure`/`StreamingProcedure`/`Subscription` objects in a dependency-neutral schema module, bind implementations with `app.rpc.bind`, and invoke them from client code through `RpcTransport` (`RpcHttpClient` / `RpcWsClient`) via `RpcCall`, `batch`, and `notify`. Contracts give pyright full checking — nonexistent methods, wrong param types, and result mismatches are type errors — without code generation.

## Schema module

Create a `my_app/rpc_schema.py` that imports only client-safe core:

```python
from dataclasses import dataclass
from webcompy.rpc import Procedure, StreamingProcedure, Subscription

@dataclass
class AddParams:
    a: int
    b: int = 0

add = Procedure("add", AddParams, int)

@dataclass
class CountParams:
    n: int

count_up = StreamingProcedure("count_up", CountUpParams, int)

@dataclass
class TickerParams:
    ticker_id: str

@dataclass
class Tick:
    seq: int

ticker = Subscription("ticker", TickerParams, Tick, replay_size=256)
```

Schema modules must not import `webcompy_server`, Starlette, or other server-only libraries. The app package is already shipped to the browser bundle, so importing the schema from both sides adds no extra dependency.

## Binding

Server implementations live in a separate server-only module that imports the schema and binds:

```python
from my_app.rpc_schema import AddParams, add, count_up, ticker

def _add(p: AddParams) -> int:
    return p.a + p.b

app.rpc.bind(add, _add)

# decorator sugar
@app.rpc.bind(count_up)
async def _count_up(p: CountUpParams) -> AsyncIterator[int]:
    for i in range(1, p.n + 1):
        yield i

@app.rpc.bind(ticker)
async def _ticker(p: TickerParams) -> AsyncIterator[Tick]:
    ...
```

`bind(contract, impl)` validates at registration:

- `Procedure`: `impl` must not be a generator, must take exactly one parameter whose annotation equals `params_type`, and must return `result_type`. Iterable-annotated non-generators are rejected.
- `StreamingProcedure`: `impl` must be a generator with a subscripted `AsyncIterator[T]`/`Iterator[T]` etc., element `T` must equal `result_type`.
- `Subscription`: `impl` must be an async generator with `AsyncIterator[T]` / `AsyncGenerator[T, None]`, `T` must equal `event_type`. `replay_size` from the contract flows to the subscription buffer.

Name collisions and reserved `_webcompy.*` names are rejected. Drift between schema and implementation becomes a startup error.

## Transports

Contracts are transport-agnostic. Pass an explicit `RpcTransport`:

- `RpcHttpClient()` — browser + SSR. `call`/`notify`/`stream` delegate to the HTTP JSON-RPC endpoint (`/_webcompy-rpc`). During SSR, `call` and `batch` dispatch in-process and are baked into the hydration payload (`batch` as a single `POST:/_webcompy-rpc:[...]` entry); `notify` is not baked (HTTP `204`). `subscribe` raises `RpcError`.
- `RpcWsClient` — browser, shared auto-reconnecting WebSocket. Implements `call`/`notify`/`stream`/`subscribe`. In-flight calls fail with `RpcError` on disconnect; subscriptions heal via rejoin.

## Calls, batch, notify

`Procedure` is invoked as `proc(transport, params) -> RpcCall[P, R]` (`Awaitable[R]`). `await` performs the call:

```python
from webcompy.rpc import batch, notify
from webcompy.rpc._contracts import RpcHttpClient

client = RpcHttpClient()
value: int = await add(client, AddParams(a=2, b=3))
```

`RpcCall` is usable in `batch` and `notify` before awaiting. Double-await raises `RuntimeError`; `bool(RpcCall)` and `len(RpcCall)` raise `TypeError`.

Typed batch over `RpcCall`:

```python
c1 = add(client, AddParams(a=1))
c2 = add(client, AddParams(a=2))
results: tuple[int, int] = await batch(c1, c2)  # one POST array / one WS frame
empty: tuple[()] = await batch()                # no I/O
with_errors: tuple[int | RpcError, ...] = await batch(c1, missing, return_exceptions=True)
```

Fire-and-forget notify as an id-less array:

```python
await notify(add(client, AddParams(a=1)), add(client, AddParams(a=2)))
await notify()  # no I/O
```

`batch`/`notify` require all calls to share the same transport instance; mixed transports raise `RpcError`. Streaming and subscription calls are rejected by both.

## SSR semantics

Contracts work in both environments; behavior is determined by the transport. `RpcHttpClient` during SSR/SSG bakes `call`/`batch` results; `notify` is dispatched but not baked. `RpcWsClient` in SSR emits a warning and is a no-op; subscriptions return a closed iterator.

## Non-goals

- No code generation — contracts are hand-written runtime objects with PEP 695 generics.
- No per-parameter call syntax — params are a single dataclass object.
- No changes to the JSON-RPC wire, `meta` codec, replay/rejoin, or `RpcStream`/`RpcSubscription` handles (`batch`/`notify` reuse the existing batch wire as an id-less array).
- No `use_rpc` composable — transports are passed explicitly.
