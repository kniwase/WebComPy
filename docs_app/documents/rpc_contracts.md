---
title: RPC Contracts
description: Primary entry point for typed WebComPy RPC — transport routing guide, shared Procedure/StreamingProcedure/Subscription contracts, batch and notify helpers, server binding, and middleware.
---

# RPC Contracts

Declarative RPC contracts are the primary way to build typed client-server APIs in WebComPy. You declare `Procedure`, `StreamingProcedure`, and `Subscription` objects once in a shared module, bind implementations on the server with `@app.rpc.bind(...)`, and invoke them from browser or SSR code through `RpcHttpClient` or `RpcWsClient` with end-to-end `pyright` type checking and zero code generation.

## Choosing the right transport

| Use case | API | Transport | Key behavior |
|---|---|---|---|
| Public REST endpoints, static JSON assets, third-party APIs | [`HttpClient` / `use_async_result`](/documents/basic/http-and-async) | Plain HTTP (`GET`/`POST`/...) | Arbitrary REST URLs, HTTP status codes, initial fetch baked during SSR |
| One-way server push of text events | [`use_event_source`](/documents/advanced/event-source) | SSE (`GET` or streaming `fetch`) | Named events, shared per-URL connection, auto-reconnect + `Last-Event-ID`, browser-only |
| Raw bidirectional text or custom JSON frames | [`use_websocket`](/documents/advanced/websocket) / [Typed Realtime](/documents/advanced/typed-realtime) | WebSocket | Shared `(url, protocols)` socket, backoff/jitter, optional dataclass frames, browser-only |
| Typed request/response queries & mutations | `Procedure` + [`RpcHttpClient`](/documents/advanced/rpc) | HTTP `POST` (`/_webcompy-rpc`) | Strict dataclass schemas, `batch()`, `notify()`, middleware, SSR/SSG result baking |
| Finite call-scoped typed streams | `StreamingProcedure` + [`RpcStream`](/documents/advanced/rpc-streaming) | HTTP SSE or WebSocket | `async for` over generator output, `stream.close()` cancels server generator |
| Long-lived pub/sub + low-latency calls | `Subscription` / `Procedure` + [`RpcWsClient`](/documents/advanced/rpc-websocket) | WebSocket (`/_webcompy-rpc`) | Shared socket, auto-rejoin with cursor replay, heartbeat, browser-only |

## When to use

- **Need typed server procedures with compile-time checking** — start here with `Procedure`, `StreamingProcedure`, and `Subscription`.
- **Configuring HTTP dispatcher routes or manual transport fallback** — see [RPC](/documents/advanced/rpc).
- **Streaming finite server generator outputs per request** — see [RPC Streaming](/documents/advanced/rpc-streaming).
- **Subscribing to shared cursor-replayed event feeds** — see [RPC over WebSocket](/documents/advanced/rpc-websocket).
- **Calling existing REST endpoints outside WebComPy** — stick with [HTTP & Async](/documents/basic/http-and-async).

## Setup

Split an RPC feature across three pieces: a shared contracts module imported by both client and server, server-side bindings on `app.rpc`, and component calls using `RpcHttpClient` (or `RpcWsClient`).

```python
# my_app/contracts.py — shared by server and browser
from dataclasses import dataclass

from webcompy.rpc import Procedure


@dataclass
class GetUserParams:
    id: int


@dataclass
class User:
    id: int
    name: str
    role: str


get_user = Procedure("users.get", GetUserParams, User)
```

Bind the server implementation in your app package and mount either via `webcompy start` (automatic whenever `app.rpc` has bindings) or an explicit Starlette host:

```python
# my_app/server.py — Starlette / WebComPy server side
from starlette.applications import Starlette
from starlette.routing import Route

from webcompy import WebComPyApp
from webcompy_server.rpc import create_dispatcher_app
from my_app.contracts import GetUserParams, User, get_user


def register_procedures(app: WebComPyApp) -> None:
    @app.rpc.bind(get_user)
    async def handle_get_user(params: GetUserParams) -> User:
        return User(id=params.id, name="Ada Lovelace", role="admin")


# Auto-mounted by `webcompy start` / `webcompy serve` at app.rpc.path (default "/_webcompy-rpc"),
# or mounted explicitly inside an existing Starlette host:
# host = Starlette(routes=[Route(app.rpc.path, create_dispatcher_app(app.rpc))])
```

Invoke the same `get_user` contract in a component with `RpcHttpClient()`:

```python
# my_app/components/user_card.py — client / SSR component side
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.elements import html
from webcompy.rpc import RpcHttpClient
from my_app.contracts import GetUserParams, get_user

client = RpcHttpClient()


@define_component()
def UserCard(context: ComponentContext[None]):
    user_req = use_async_result(lambda: get_user(client, GetUserParams(id=1)))

    return html.P(
        {},
        use_computed(
            lambda: f"{user_req.data.value.name} ({user_req.data.value.role})"
            if user_req.data.value is not None
            else "Loading..."
        ),
    )
```

## Recipes

### Call a `Procedure` and handle `RpcError`

Every bound procedure receives its validated dataclass parameter and returns the declared result type. Server errors surface on the client as `RpcError` with `.code`, `.message`, and optional `.data`:

```python
# Server registration
from dataclasses import dataclass
from webcompy.rpc import Procedure, RpcError


@dataclass
class DivideParams:
    numerator: int
    denominator: int


@dataclass
class Quotient:
    value: float


divide = Procedure("math.divide", DivideParams, Quotient)


@app.rpc.bind(divide)
def handle_divide(params: DivideParams) -> Quotient:
    if params.denominator == 0:
        raise RpcError(-32001, "Division by zero", data={"field": "denominator"})
    return Quotient(value=params.numerator / params.denominator)
```

```python
# Client call
from webcompy.rpc import RpcError, RpcHttpClient

client = RpcHttpClient()

try:
    res = await divide(client, DivideParams(numerator=10, denominator=0))
except RpcError as err:
    print(err.code, err.message, err.data)
```

### Batch multiple calls and send notifications

Group independent `RpcCall` objects with `batch(...)` to send one JSON-RPC batch array over HTTP or WebSocket and unpack strongly typed results in order. Use `notify(...)` for fire-and-forget calls that omit request `id` and expect no response:

```python
# Server registration
from dataclasses import dataclass
from webcompy.rpc import Procedure


@dataclass
class EmptyParams:
    pass


@dataclass
class AuditParams:
    action: str


@dataclass
class EmptyResult:
    ok: bool = True


@dataclass
class Stats:
    users: int


@dataclass
class Notice:
    text: str


get_stats = Procedure("dashboard.stats", EmptyParams, Stats)
get_notice = Procedure("dashboard.notice", EmptyParams, Notice)
record_audit = Procedure("audit.record", AuditParams, EmptyResult)


@app.rpc.bind(get_stats)
async def handle_stats(_params: EmptyParams) -> Stats:
    return Stats(users=42)


@app.rpc.bind(get_notice)
async def handle_notice(_params: EmptyParams) -> Notice:
    return Notice(text="System healthy")


@app.rpc.bind(record_audit)
async def handle_audit(params: AuditParams) -> EmptyResult:
    # persist audit event
    return EmptyResult()
```

```python
# Client batch + notify
from webcompy.rpc import RpcError, RpcHttpClient, batch, notify

client = RpcHttpClient()

# Fail fast on first error (default return_exceptions=False)
stats, notice = await batch(
    get_stats(client, EmptyParams()),
    get_notice(client, EmptyParams()),
)

# Or inspect per-entry errors individually
results = await batch(
    get_stats(client, EmptyParams()),
    get_notice(client, EmptyParams()),
    return_exceptions=True,
)
for entry in results:
    if isinstance(entry, RpcError):
        print("Call failed:", entry.message)

# Fire-and-forget notification (HTTP 204, no response payload)
await notify(record_audit(client, AuditParams(action="viewed_dashboard")))
```

### Add auth headers or test mocks with `RpcMiddleware`

Install HTTP RPC middleware inside component setup (in the active render DI scope) via `add_rpc_middleware` to attach authorization headers or short-circuit requests with synthetic responses during local UI work. This mirrors the `add_fetch_middleware` pattern introduced in [Step 5: Remote Data](/documents/guides/todo-remote-data) (and dedicated Advanced middleware docs will cover composition in detail):

```python
# Server procedure using standard endpoint
from dataclasses import dataclass
from webcompy.rpc import Procedure


@dataclass
class SecretParams:
    scope: str


@dataclass
class SecretData:
    token: str


read_secret = Procedure("auth.secret", SecretParams, SecretData)


@app.rpc.bind(read_secret)
async def handle_secret(params: SecretParams) -> SecretData:
    return SecretData(token=f"scoped:{params.scope}")
```

```python
# Client component installing auth header middleware
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.elements import html
from webcompy.rpc import RpcContext, RpcHttpClient, add_rpc_middleware

client = RpcHttpClient()


@define_component()
def ProtectedPanel(context: ComponentContext[None]):
    async def attach_bearer(ctx: RpcContext, next):
        ctx.headers["Authorization"] = "Bearer demo-token"
        return await next(ctx)

    add_rpc_middleware(attach_bearer)
    secret = use_async_result(lambda: read_secret(client, SecretParams(scope="read")))

    return html.P(
        {},
        use_computed(
            lambda: secret.data.value.token if secret.data.value is not None else "..."
        ),
    )
```

For `batch(...)`, `ctx.is_batch` is `True`, `ctx.method` is `""`, and `ctx.batch_entries` lists each `RpcBatchEntry` in order. In middleware tests or serverless previews, `return await next(response={"result": ...})` skips the network round trip while still enforcing contract schema validation.

### Register custom types on the RPC registry

Built-in codecs handle standard JSON primitives plus `datetime`, `date`, `time`, `timedelta`, `UUID`, `Decimal`, `bytes`, `set`, `frozenset`, `tuple`, `re.Pattern`, `Enum`, and nested dataclasses. Register domain types on `app.rpc` in shared setup so both server serialization and client deserialization allowlist the tag:

```python
# Shared contracts + codec registration (imported by server and client)
from dataclasses import dataclass

from webcompy import WebComPyApp
from webcompy.rpc import Procedure


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass
class MoveParams:
    target: Point


@dataclass
class MoveResult:
    location: Point


move_marker = Procedure("map.move", MoveParams, MoveResult)


def configure_rpc_types(app: WebComPyApp) -> None:
    app.rpc.register_type_handler(
        Point,
        encoder=lambda p: {"x": p.x, "y": p.y},
        decoder=lambda d: Point(x=d["x"], y=d["y"]),
    )
```

```python
# Server registration
@app.rpc.bind(move_marker)
async def handle_move(params: MoveParams) -> MoveResult:
    return MoveResult(location=Point(x=params.target.x + 1.0, y=params.target.y))
```

```python
# Client call (after configure_rpc_types(app) runs on bootstrap)
from webcompy.rpc import RpcHttpClient

client = RpcHttpClient()
moved = await move_marker(client, MoveParams(target=Point(x=2.0, y=5.0)))
```

## Behavior notes

- **Binding validation at startup**: `app.rpc.bind(contract, impl)` verifies that the implementation has concrete type annotations matching `contract.params_type` and `contract.result_type` (or `AsyncIterator[E]` / `AsyncGenerator[E, None]` for `Subscription`). Generator functions must match `StreamingProcedure`, async generators match `StreamingProcedure` or `Subscription`, and `_webcompy.*` method names are rejected everywhere.
- **Single-use `RpcCall` objects**: `contract(client, params)` returns an `RpcCall` (for `Procedure`) that can be awaited once or passed once to `batch(...)` / `notify(...)`. Awaiting or reusing the same `RpcCall` twice raises `RuntimeError`. Checking `bool(call)` or `len(call)` raises `TypeError` to catch a forgotten `await`.
- **Transport capability matrix**:
  - `RpcHttpClient`: supports `Procedure` (single, `batch`, `notify`) and `StreamingProcedure` (SSE over HTTP `POST`); calling a `Subscription` raises `RpcError`.
  - `RpcWsClient`: supports `Procedure` (single, `batch`, `notify`), `StreamingProcedure`, and `Subscription`; fails with `RpcError` if called before the socket reaches `OPEN` or when disconnected.
- **SSR and hydration**: During server rendering and `webcompy generate`, `RpcHttpClient` dispatches `Procedure` calls and `batch(...)` in-process and caches results in `<script id="__webcompy_data__">` (`batch(...)` caches a single array key under `POST:/_webcompy-rpc:[...]`). `notify(...)` executes without baking into the hydration cache. `RpcWsClient` logs a warning and performs no socket operations on the server.

## Pitfalls

- **Importing server-only dependencies inside the contract module**: Your client wheel also executes the contracts module in PyScript. Keep database drivers, ORM models, and filesystem secrets strictly in server handler modules imported only on CPython.
- **Forgetting `await` on `Procedure` calls**: `get_user(client, params)` returns a lazy `RpcCall`, not the result. Passing it directly into a reactive expression or `if` condition raises `TypeError` until awaited.
- **Mixing transports inside one `batch(...)` or `notify(...)`**: All calls passed to a single `batch(...)` or `notify(...)` must share the same `RpcHttpClient` or `RpcWsClient` instance; mixing transports raises `RpcError`.
- **Non-dataclass `params_type`**: `Procedure`, `StreamingProcedure`, and `Subscription` all require `params_type` to be a `@dataclass` class (use an empty dataclass such as `EmptyParams` when a method needs no fields).
- **Returning from `RpcMiddleware` without calling `await next(...)`**: Middleware must delegate via `await next(...)` (or `await next(ctx, response=...)`); returning a bare value directly raises `RuntimeError` rather than bypassing result validation.

## Next steps

- Inspect HTTP transport internals, custom endpoint paths, Starlette mounting, and the manual transport appendix in [RPC](/documents/advanced/rpc).
- Stream finite request-scoped generator outputs in [RPC Streaming](/documents/advanced/rpc-streaming).
- Run cursor-replayed pub/sub feeds and multiplexed calls over one socket in [RPC over WebSocket](/documents/advanced/rpc-websocket).
- Review plain REST fetching and mock middleware in [HTTP & Async](/documents/basic/http-and-async) and [Step 5: Remote Data](/documents/guides/todo-remote-data).
