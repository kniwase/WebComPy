---
title: RPC
description: HTTP transport for WebComPy JSON-RPC — RpcHttpClient, Starlette dispatcher mounting, strict typed decoding, error handling, SSR baking, and manual transport appendix.
---

# RPC

WebComPy's HTTP RPC layer runs declarative `Procedure` and `StreamingProcedure` contracts over JSON-RPC 2.0 `POST` requests via `RpcHttpClient` and the server ASGI dispatcher. If you are starting from scratch, start with [RPC Contracts](/documents/advanced/rpc-contracts) first to define shared contracts; use this page when configuring the HTTP transport, mounting the dispatcher in Starlette, handling `RpcError` codes, or dropping down to manual transport calls.

## When to use

- **Declaring new typed procedures, batches, or notifications** — define them in [RPC Contracts](/documents/advanced/rpc-contracts) and execute with `RpcHttpClient`.
- **Configuring endpoint paths, custom Starlette ASGI hosts, error handling, or HTTP SSR caching** — read this page.
- **Need cursor-replayed subscriptions or persistent bidirectional RPC** — use [RPC over WebSocket](/documents/advanced/rpc-websocket).
- **Need finite call-scoped server streams** — use [RPC Streaming](/documents/advanced/rpc-streaming).

## Setup

Define a shared `Procedure` contract, bind the server implementation on `app.rpc`, and call it from `RpcHttpClient`. When serving with `webcompy start` or `webcompy serve`, WebComPy automatically mounts HTTP and WebSocket dispatchers at `app.rpc.path` (default `/_webcompy-rpc`) whenever `app.rpc.has_procedures` is `True`. To embed inside your own Starlette host app, mount `create_dispatcher_app(app.rpc)`:

```python
# Server setup (app + optional Starlette host)
from dataclasses import dataclass

from starlette.applications import Starlette
from starlette.routing import Route

from webcompy import WebComPyApp, use_computed
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.elements import html
from webcompy.rpc import Procedure, RpcHttpClient
from webcompy_server.rpc import create_dispatcher_app


@dataclass
class PingParams:
    message: str


@dataclass
class PingReply:
    echo: str


ping = Procedure("system.ping", PingParams, PingReply)


@define_component()
def RootView(context: ComponentContext[None]):
    client = RpcHttpClient()
    reply = use_async_result(lambda: ping(client, PingParams(message="hello")))

    return html.P(
        {},
        use_computed(lambda: reply.data.value.echo if reply.data.value is not None else "..."),
    )


app = WebComPyApp(RootView)


@app.rpc.bind(ping)
async def handle_ping(params: PingParams) -> PingReply:
    return PingReply(echo=params.message)


# Needed only when embedding WebComPy inside a custom Starlette/FastAPI host:
host_app = Starlette(
    routes=[
        Route(app.rpc.path, create_dispatcher_app(app.rpc)),
    ]
)
```

If you call `app.rpc.bind(...)` inside a normal WebComPy package served via `webcompy start`, no extra `Route(...)` wiring is required.

## Recipes

### Mount on a custom path and compute `base_url`-aware endpoints

Call `app.rpc.set_path(path)` before serving (for example, in app bootstrap) to move both server dispatcher routing and client requests from `/_webcompy-rpc` to an arbitrary non-root path such as `"/api/rpc"`:

```python
# Server configuration
from webcompy import WebComPyApp, WebComPyAppConfig
from webcompy.rpc import Procedure, RpcHttpClient
from webcompy_server.rpc import create_dispatcher_app
from starlette.routing import Route


def configure_app(app: WebComPyApp) -> None:
    app.rpc.set_path("/api/rpc")

    @app.rpc.bind(ping)
    async def handle_ping(params: PingParams) -> PingReply:
        return PingReply(echo=params.message)


# If app.config.base_url is "/portal", app.rpc.endpoint_url resolves to "/portal/api/rpc".
# Mount explicitly on a custom Starlette host if not using `webcompy start`:
# Route(app.rpc.path, create_dispatcher_app(app.rpc))
```

```python
# Client call automatically posts to app.rpc.endpoint_url
client = RpcHttpClient()
reply = await ping(client, PingParams(message="custom path"))
```

### Handle structured JSON-RPC errors with `RpcError`

Raise `RpcError(code, message, data=...)` from server procedures for predictable client error handling, and catch `RpcError` in browser handlers or `ErrorBoundary` views:

```python
# Server registration
from dataclasses import dataclass
from webcompy.rpc import Procedure, RpcError


@dataclass
class LookupParams:
    slug: str


@dataclass
class Article:
    slug: str
    title: str


get_article = Procedure("docs.get", LookupParams, Article)


@app.rpc.bind(get_article)
async def handle_get_article(params: LookupParams) -> Article:
    if params.slug != "intro":
        raise RpcError(-32004, "Article not found", data={"slug": params.slug})
    return Article(slug="intro", title="Introduction")
```

```python
# Client handling
from webcompy.rpc import RpcError, RpcHttpClient

client = RpcHttpClient()

try:
    article = await get_article(client, LookupParams(slug="missing"))
except RpcError as err:
    # Standard JSON-RPC 2.0 codes:
    # -32700 Parse error | -32600 Invalid Request | -32601 Method not found
    # -32602 Invalid params | -32603 Internal error | -32000..-32099 Server errors
    print(f"[{err.code}] {err.message} -> {err.data}")
```

Unhandled Python exceptions inside a server procedure are logged server-side and returned to clients as a generic `-32603` internal error without leaking stack traces.

### Inspect or decorate HTTP RPC calls with `add_rpc_middleware`

Install `RpcMiddleware` inside component setup to inject per-request headers (such as CSRF tokens or bearer tokens) across `Procedure`, `batch`, `notify`, and HTTP `StreamingProcedure` calls:

```python
# Server procedure reading standard bound inputs
@app.rpc.bind(ping)
async def handle_ping_authed(params: PingParams) -> PingReply:
    return PingReply(echo=f"accepted:{params.message}")
```

```python
# Client middleware registered in component setup
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.elements import html
from webcompy.rpc import RpcContext, RpcHttpClient, add_rpc_middleware

client = RpcHttpClient()


@define_component()
def AuthedPing(context: ComponentContext[None]):
    async def add_trace_header(ctx: RpcContext, next):
        ctx.headers["X-Client-Trace"] = "webcompy-ui"
        return await next(ctx)

    add_rpc_middleware(add_trace_header)
    result = use_async_result(lambda: ping(client, PingParams(message="ok")))

    return html.SPAN(
        {},
        use_computed(
            lambda: result.data.value.echo if result.data.value is not None else "Pending"
        ),
    )
```

For full middleware composition details, see [Middleware](/documents/advanced/middleware) (same DI-scoped registry pattern as `add_fetch_middleware`).

## Behavior notes

- **Strict server-side decoding & allowlist**: Contract procedures expect object-form `params` and reconstruct them with `from_json(params_type, params, strict=True)`. Positional JSON array `params` (e.g. `[5]`) are rejected with `-32602`. Metadata type restoration (`meta`) only decodes built-in tags and custom classes explicitly added via `app.rpc.register_type_handler(...)`; arbitrary client class names are never imported.
- **JSON-RPC 2.0 HTTP status conventions**: Single calls and mixed batches return HTTP `200` with JSON response bodies. Standalone `notify(...)` calls and all-notification batches return HTTP `204` with an empty response body (never `[]`). Empty batch arrays `[]` and malformed JSON return JSON-RPC errors (`-32600` / `-32700`).
- **SSR and hydration baking**: During server rendering and `webcompy generate`, `RpcHttpClient` routes `Procedure` calls and `batch(...)` in-process through `ServerFetchPort` (bypassing network HTTP) and records responses in `<script id="__webcompy_data__">`. On initial browser boot, matching calls replay from cache without duplicate network requests. `notify(...)` executes without adding a hydration entry.
- **Conditional route mounting**: When `app.rpc.has_procedures` is `False`, `webcompy start` and `webcompy serve` skip adding `/_webcompy-rpc` to the ASGI route table altogether.

## Pitfalls

- **Modifying `Content-Type` inside RPC middleware**: `RpcHttpClient` resets `Content-Type` case-insensitively back to `application/json` after all middlewares contribute `ctx.headers`, so custom media types cannot break dispatcher parsing.
- **Binding procedures after building the ASGI app**: `create_asgi_app()` and `create_dispatcher_app(app.rpc)` read `app.rpc` at startup/dispatch time; always call `app.rpc.set_path(...)` and bind all contracts before starting the server.
- **Calling mutations on a statically exported (`webcompy generate`) site**: Pre-rendering bakes initial SSR `Procedure` reads into static HTML, but static file hosting has no Python POST dispatcher at runtime. Live HTTP RPC mutations require `webcompy start`, `webcompy serve`, or an ASGI host mounting `create_dispatcher_app(app.rpc)`.

## Manual transport (rarely needed)

Under the hood, every `Procedure` or `StreamingProcedure` delegates to low-level methods directly on `RpcHttpClient` (`webcompy.rpc`). Avoid leading application code with raw string method names — contracts give you static type checking on parameter and result schemas — but knowing the transport primitives helps when building dynamic adapters or tooling:

```python
from webcompy.rpc import RpcHttpClient

client = RpcHttpClient()

# Manual string-method HTTP call (bypasses static contract checking)
user = await client.call("users.get", {"id": 1}, result_type=User)

# Manual string-method notification (no id, HTTP 204)
await client.notify("audit.record", {"action": "manual_ping"})

# Manual string-method finite stream (SSE over POST)
stream = client.stream("tokens.generate", {"prompt": "hi"}, result_type=TokenChunk)
```

Server metadata and endpoint inspection remain accessible on `app.rpc` (`ProcedureRegistry`):

- `app.rpc.path` — configured endpoint path (default `"/_webcompy-rpc"`).
- `app.rpc.endpoint_url` — `base_url` combined with `app.rpc.path`.
- `app.rpc.has_procedures` — `True` if at least one procedure, streaming procedure, or subscription is bound.
- `app.rpc.register_type_handler(cls, encoder, decoder)` — registers allowlisted custom serialization codecs shared across contracts and manual transport payloads.

## Next steps

- See `Procedure` calls and `batch()` mocked via `RpcMiddleware` in the [RPC Middleware](/documents/examples/rpc-middleware) example.
- Start with contract declarations, `batch()`, and `notify()` in [RPC Contracts](/documents/advanced/rpc-contracts).
- Use long-lived subscriptions and low-latency multiplexed calls in [RPC over WebSocket](/documents/advanced/rpc-websocket).
- Stream finite call-scoped generator outputs in [RPC Streaming](/documents/advanced/rpc-streaming).
- Understand in-process SSR dispatch and hydration payload replay in [SSR & SSG](/documents/advanced/ssr-and-ssg) and [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
- Full API: [Server, CLI, RPC & Ports API](/documents/api/server-and-cli).
