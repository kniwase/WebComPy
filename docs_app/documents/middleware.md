---
title: Middleware
description: Intercept HTTP and JSON-RPC operations with stackable FetchMiddleware and RpcMiddleware chains, DI-scoped additive registries, streaming header resolution, and plugin hooks.
---

# Middleware

WebComPy separates port transport implementations (`FetchPort`) from cross-cutting HTTP and RPC policies (`FetchMiddleware` and `RpcMiddleware`). You register async interceptors in an active DI scope — from components or plugins — to inject auth headers, record timings or caches, and return validated synthetic responses without replacing `FetchPort` or bypassing SSR hydration caches and blocked-path guards.

## When to use

- **Need auth headers, telemetry, retries, or offline mocks around `HttpClient` or SSE/fetch streams** — use `FetchMiddleware` via `add_fetch_middleware`.
- **Want typed interception on HTTP JSON-RPC (`Procedure`, `batch`, `notify`, HTTP `StreamingProcedure`)** — use `RpcMiddleware` via `add_rpc_middleware` (see also [RPC Contracts](/documents/advanced/rpc-contracts) and [RPC Streaming](/documents/advanced/rpc-streaming)).
- **Swapping out an entire port in unit tests** — override the port directly inside `DIScope` (see [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive)).
- **Sharing middlewares cleanly across applications** — bundle them in a `WebComPyPlugin` (see [Plugins](/documents/advanced/plugins)).

## Setup

Install fetch middlewares through `add_fetch_middleware` (`webcompy.ports`) and RPC middlewares through `add_rpc_middleware` (`webcompy.rpc`) inside component setup or plugin hooks:

```python
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.ajax import HttpClient
from webcompy.elements import html
from webcompy.ports import FetchNext, FetchRequest, add_fetch_middleware
from webcompy import use_computed


@define_component()
def ApiConsumer(context: ComponentContext[None]):
    async def attach_auth(request: FetchRequest, next: FetchNext):
        request.headers = {**(request.headers or {}), "Authorization": "Bearer token"}
        return await next(request)

    add_fetch_middleware(attach_auth)
    profile = use_async_result(lambda: HttpClient.get("/api/profile"))

    return html.P(
        {},
        use_computed(
            lambda: profile.data.value.text if profile.data.value is not None else "Loading..."
        ),
    )
```

Chains compose **outside-in** in registration order (`middlewares[0]` is outermost):

```text
Request   ──► middlewares[0] ──► middlewares[1] ──► concrete FetchPort / dispatcher
Response  ◄── middlewares[0] ◄── middlewares[1] ◄── concrete FetchPort / dispatcher
```

## Recipes

### 1. Inject authentication or tracing headers (`FetchMiddleware` & `RpcMiddleware`)

Mutate `request.headers` (on `FetchRequest`) or `ctx.headers` (on `RpcContext`) before delegating to `await next(...)`:

```python
# FetchMiddleware for REST / HttpClient / non-GET SSE endpoints
from webcompy.ports import FetchNext, FetchRequest, add_fetch_middleware

async def trace_fetch_middleware(request: FetchRequest, next: FetchNext):
    request.headers = {**(request.headers or {}), "X-Trace-Id": "req-123"}
    return await next(request)
```

```python
# RpcMiddleware operates on typed contract objects before JSON-RPC encoding
from webcompy.rpc import RpcContext, add_rpc_middleware

async def auth_rpc_middleware(ctx: RpcContext, next):
    ctx.headers["Authorization"] = "Bearer session-token"
    if ctx.method.startswith("admin."):
        ctx.headers["X-Admin-Scope"] = "1"
    return await next(ctx)
```

On `RpcMiddleware`, `ctx.params` holds the typed dataclass instance before wire serialization, and for `batch(...)` calls `ctx.is_batch` is `True`, `ctx.method` is `""`, and `ctx.batch_entries` lists each `RpcBatchEntry` in call order.

### 2. Log timings and cache responses around `await next(...)`

Code before `await next(...)` runs on the outbound leg; code after it sees the returned `Response`, `FetchStream`, or decoded RPC result:

```python
import time
from webcompy.ports import FetchNext, FetchRequest, Response


def make_timing_cache_middleware():
    cache: dict[str, Response] = {}

    async def timing_cache(request: FetchRequest, next: FetchNext):
        if request.method == "GET" and request.url in cache:
            return await next(request, response=cache[request.url])

        started = time.monotonic()
        response = await next(request)
        elapsed_ms = (time.monotonic() - started) * 1000
        if isinstance(response, Response) and request.method == "GET" and response.ok:
            cache[request.url] = response
        print(f"{request.method} {request.url} -> {response.status_code} ({elapsed_ms:.1f}ms)")
        return response

    return timing_cache
```

Passing `await next(request, response=cached)` short-circuits remaining inner middlewares and the concrete `FetchPort` while returning `cached` cleanly through outer layers.

### 3. Build offline mocks without losing schema validation

Both middleware layers let client apps run serverless demos on static hosting (`webcompy generate`) while preserving normal HTTP and RPC validation — the exact pattern introduced in [Step 5: Remote Data](/documents/guides/todo-remote-data) (and used in standalone middleware demos):

```python
import json
from webcompy.ports import FetchNext, FetchRequest, Response, add_fetch_middleware
from webcompy.rpc import RpcContext, add_rpc_middleware


async def offline_rest_mock(request: FetchRequest, next: FetchNext):
    if request.url == "/api/tasks" and request.method == "GET":
        return Response(
            text=json.dumps([{"id": 1, "title": "Ship docs", "done": True}]),
            headers={"Content-Type": "application/json"},
            status_code=200,
            status_text="OK",
            ok=True,
        )
    return await next(request)


async def offline_rpc_mock(ctx: RpcContext, next):
    if ctx.method == "users.get":
        # Routed through apply_transfer_meta + schema validation just like a live response
        return await next(ctx, response={"result": {"id": 1, "name": "Ada", "role": "admin"}})
    return await next(ctx)
```

For streaming HTTP RPC procedures (`StreamingProcedure`), pass `stream=` (`await next(ctx, stream=synthetic_fetch_stream)`) to substitute an SSE `FetchStream` whose chunks still pass through per-item typed decoding. See [RPC Streaming](/documents/advanced/rpc-streaming) for a complete `FetchStream` mock example.

## Behavior notes

- **DI-scoped additive registries**: Both `FETCH_MIDDLEWARE_KEY` (`FetchMiddlewareRegistry`) and `RPC_MIDDLEWARE_KEY` (`RpcMiddlewareRegistry`) are created fresh per `RenderContext`, resolved through the active `DIScope`, and disposed when the context ends. Because `provide()` overwrites keys while `.use()` appends, always call `add_fetch_middleware()` / `add_rpc_middleware()` (or `registry.use(...)`) rather than re-providing the registry key.
- **Plugin aggregation order**: `PluginManager.init_render_context()` reads `get_fetch_middlewares()` and `get_rpc_middlewares()` across `WebComPyAppConfig.plugins` in declaration order and appends them before component setup runs — so plugin middlewares sit outermost relative to component-installed middlewares.
- **Streaming header-commit timing**: On `FetchPort.stream()` calls, `await next(request)` resolves once response `status_code`, `headers`, and `ok` are committed — before any body chunks are consumed. Middleware can inspect status/headers or return a substitute `FetchStream` without downstream consumers noticing.
- **SSR hydration & blocked-path delegation**: WebComPy's wrapped `FetchPort` delegates `populate_from_transfer`, `get_transfer_data`, `clear_cache`, `close`, `is_self_site_url`, and the server `noop` marker to the inner concrete port. Self-site SSR recursion blocking and hydration response caching remain intact even with arbitrary fetch middlewares installed.
- **HTTP-only RPC interception**: `RpcMiddleware` applies to HTTP operations (`RpcHttpClient.call`, `notify`, `batch`, `stream`). `RpcWsClient` operations bypass `RpcMiddleware`.

## Pitfalls

- **Returning from `RpcMiddleware` without calling `await next(...)`**: Unlike `FetchMiddleware` (which allows returning a `Response` directly without `next`), returning a bare value from `RpcMiddleware` without delegating to `next` raises `RuntimeError` so schema/metadata validation can never be skipped. Always call `await next(ctx, response=...)` (or `stream=...`).
- **Overwriting `Content-Type` in `RpcMiddleware`**: WebComPy resets `Content-Type` (case-insensitively) to `application/json` after all RPC middlewares run so handlers cannot corrupt the JSON-RPC wire format.
- **Registering middlewares at module import time**: Outside an active render context, `add_fetch_middleware` / `add_rpc_middleware` fall back to the app scope or raise `InjectionError` if no app scope exists — causing cross-request state or test leakage. Register inside component setup, `DIScope`, or plugin hooks.
- **Replacing `FETCH_MIDDLEWARE_KEY` via `provide()`**: Replacing the registry key drops middlewares contributed earlier by plugins or ancestor setup. Always append with `add_*_middleware()`.

## Next steps

- Understand the scope lifecycle and per-request port isolation behind middleware registries in [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive).
- Package fetch and RPC middlewares into reusable extensions in [Plugins](/documents/advanced/plugins).
- Apply `RpcMiddleware` to typed contracts and streams in [RPC Contracts](/documents/advanced/rpc-contracts), [RPC](/documents/advanced/rpc), and [RPC Streaming](/documents/advanced/rpc-streaming).
- Review basic `HttpClient` requests and Step 5's `FetchMiddleware` API mock in [HTTP & Async](/documents/basic/http-and-async) and [Step 5: Remote Data](/documents/guides/todo-remote-data).
