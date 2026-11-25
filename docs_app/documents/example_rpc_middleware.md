---
title: RPC Middleware
description: Contract-first typed Procedure and batch() RPC calls answered in-browser by RpcMiddleware response synthesis, plus server registration reference.
---

# RPC Middleware

This example defines typed JSON-RPC contracts (`quote_order` and `catalog_summary` via `Procedure`) and invokes both single calls and `batch(...)` through `RpcHttpClient`. An in-app `RpcMiddleware` registered with `add_rpc_middleware` intercepts every call and returns synthetic data through `await next(ctx, response=...)`, exercising the full typed deserialization and validation pipeline with zero server calls.

Use `RpcMiddleware` for auth token injection, request tracing, single-procedure or batch preview mocks, and client-side tests without bypassing contract schema validation.

## What this demonstrates

- **Typed contract declarations**: `quote_order = Procedure("orders.quote", QuoteParams, QuoteResult)` and `catalog_summary = Procedure("catalog.summary", SummaryParams, SummaryResult)` give callers end-to-end parameter and result dataclass checking.
- **Validated mock synthesis (`await next(ctx, response=...)`)**: Returning through `next(ctx, response=...)` routes synthetic dicts through WebComPy's `_resolve_single` and `from_json` pipeline so callers still receive genuine `QuoteResult` / `SummaryResult` instances (returning a bare value without calling `next` raises `RuntimeError` explicitly).
- **Batch interception (`ctx.is_batch`)**: Clicking `"Run Batch"` dispatches both contracts together; the middleware inspects `ctx.batch_entries` and supplies an ordered list of fragments matching each entry's declared schema.

## Key mechanisms and how to adapt

1. **Switch mocks cleanly for live RPC**: Conditionally skip `add_rpc_middleware(create_rpc_mock(...))` when connecting to a live backend — the `RpcHttpClient` call sites (`await quote_order(client, ...)`, `await batch(...)`) stay 100% identical.
2. **Stream mocks for `StreamingProcedure`**: When mocking a streaming RPC call, pass `await next(ctx, stream=synthetic_fetch_stream)` instead of `response=`.
3. **Read typed request params in middleware**: Before serialization, `ctx.params` (or `entry.params` inside `ctx.batch_entries`) holds the caller's live dataclass instance directly.

## Real server wiring

To back `quote_order` and `catalog_summary` with a live server instead of a browser mock, import your shared `contracts` module in your server app and bind handlers on `app.rpc`:

```python
from webcompy import WebComPyApp
from my_app.contracts import (
    QuoteParams,
    QuoteResult,
    SummaryParams,
    SummaryResult,
    catalog_summary,
    quote_order,
)

UNIT_PRICES = {"Keyboard": 120, "Monitor": 340, "Dock": 180}


def register_order_procedures(app: WebComPyApp) -> None:
    @app.rpc.bind(quote_order)
    async def handle_quote(params: QuoteParams) -> QuoteResult:
        unit_price = UNIT_PRICES.get(params.item, 100)
        return QuoteResult(
            item=params.item,
            quantity=params.quantity,
            unit_price=unit_price,
            total=unit_price * params.quantity,
        )

    @app.rpc.bind(catalog_summary)
    async def handle_summary(params: SummaryParams) -> SummaryResult:
        return SummaryResult(currency=params.currency, catalog_size=len(UNIT_PRICES))
```

When serving through `webcompy start` (or mounting `create_dispatcher_app(app.rpc)` in a host Starlette/FastAPI ASGI app), WebComPy automatically exposes `/_webcompy-rpc` for single calls, `batch(...)`, `notify(...)`, and streaming procedures.

## Next steps

- Learn declarative RPC contract design (`Procedure`, `StreamingProcedure`, `Subscription`, `batch`, `notify`) in [RPC Contracts](/documents/advanced/rpc-contracts).
- Configure HTTP RPC endpoint paths and custom Starlette mounting in [RPC](/documents/advanced/rpc).
- Inspect `FetchMiddleware` and `RpcMiddleware` composition and header rules in [Middleware](/documents/advanced/middleware).
- Review embedding a WebComPy ASGI app in Starlette/FastAPI in [ASGI Integration](/documents/server/asgi-integration).
