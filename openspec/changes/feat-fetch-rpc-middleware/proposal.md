# Proposal: feat-fetch-rpc-middleware

## Why

`FetchPort` and the HTTP RPC transport have no extension point today: the only way to alter request/response behavior (auth headers, logging, retries, testing stubs) is to replace the whole port via DI, which is all-or-nothing and bypasses hydration caching semantics. Meanwhile browser-side testing is locked to real-server behavior because `webcompy_testing.FakeFetchPort` cannot run under PyScript. Stackable middleware with an interceptor escape hatch solves both: production concerns (headers, tracing) and browser-side mocks share one mechanism.

## What Changes

- Add **`FetchMiddleware`** — stackable `(request, next)` callables around `FetchPort.fetch` and `FetchPort.stream`. `request` exposes `url`/`method`/`headers`/`body`; `next(request)` invokes the next layer. A middleware that returns without calling `next` intercepts; `next(request, response=...)` short-circuits the inner fetch while keeping downstream processing (hydration cache, RPC validation) intact.
- Add **`RpcMiddleware`** — stackable `(ctx, next)` callables around the HTTP JSON-RPC client (`call`, `notify`, `batch`, SSE streaming). `ctx` exposes procedure `method`, typed `params`, mutable `headers`, and `result_type`. `next(ctx, response={...})` synthesizes a result that still flows through `_resolve_single` validation (`apply_transfer_meta` + `from_json`). RPC middleware headers are merged onto the fixed transport headers (`Content-Type: application/json` preserved) and threaded down into the fetch layer.
- Add **middleware registries on DI** — `FETCH_MIDDLEWARE_KEY` / `RPC_MIDDLEWARE_KEY` resolve to registry objects with additive `use(middleware)` registration (DI itself is last-wins, so a registry indirection is required for distributed addition).
- Add **plugin hooks** — `WebComPyPlugin.get_fetch_middlewares()` / `get_rpc_middlewares()`, concatenated by `PluginManager` in declaration order as declarative sugar over the registries.
- Add **utility functions** — `add_fetch_middleware()` / `add_rpc_middleware()` delegating to the registries for tests and dynamic insertion.
- Chain assembly happens per `RenderContext` after `_register_ports()` and plugin initialization; ordering contract: **`middlewares[0]` is outermost** (first to see the request, last to see the response), composed via `reversed`.
- Streaming: `next` resolves when the inner layer returns a `FetchStream` — response headers are committed, body not yet consumed; synthetic streams are supported for interception.
- Both middlewares wrap both `fetch` and `stream` paths; WebSocket transports are excluded.

## Capabilities

### New Capabilities

- `fetch-middleware`: The `FetchMiddleware` type, registry/DI keys, plugin hooks, utility functions, chain composition rules, interceptor/short-circuit semantics, streaming timing, and port-delegation requirements (hydration cache, blocked paths, `noop`).
- `rpc-middleware`: The `RpcMiddleware` type, context shape, registry/DI keys, plugin hooks, header merging rules, validated synthesis via `next(response=...)`, batch/streaming coverage, and metadata-based scoping inside middleware.

### Modified Capabilities

- `port-abstraction`: `FetchPort` gains a documented middleware wrapping contract; new DI keys join `ports/_keys.py`; wrapper must delegate `populate_from_transfer` / `get_transfer_data` / `is_self_site_url` / `noop`.
- `json-rpc`: The typed browser client gains middleware hooks; `_post_envelope` headers become a merge point; validation guarantees hold for synthesized responses.
- `plugin-system`: Two new optional plugin hooks with declaration-order aggregation.
- `di-scope`: Registry objects provided via DI; additive mutation pattern documented against last-wins semantics.

## Impact

- **Code**: `packages/webcompy/src/webcompy/ports/_fetch.py` + `_keys.py` (wrapper, keys, registry), `packages/webcompy/src/webcompy/ajax/_fetch.py` (chain resolution at inject site), `packages/webcompy/src/webcompy/rpc/_client.py` + `_contracts.py` (header parameter threading, chain wrapping, validated synthesis), `packages/webcompy/src/webcompy/plugin/_plugin.py` + `_manager.py` (new hooks), `packages/webcompy/src/webcompy/app/_render_context.py` (assembly point)
- **APIs**: additive only — new types, DI keys, plugin hook methods (default no-op), utilities. No existing signature breaks; `RpcTransport.call` gains internal header plumbing without changing its public Protocol shape
- **Dependencies**: none added
- **Specs**: two new capabilities + four modified capability deltas listed above
- **Testing**: unit tests for composition order, short-circuit validation, streaming timing, hydration-cache delegation, blocked-path non-bypass; sample plugins used by docs later

## Known Issues Addressed

None directly; this provides the foundation that makes browser-side mock testing (currently impossible without a server) achievable in follow-up work.

## Non-goals

- WebSocket middleware (browser `WebSocket` API cannot carry custom headers; only `protocols` exist)
- Per-procedure middleware registration (scoping is done inside middleware using `ctx` metadata such as method name)
- Intercepting the `HttpClient` multipart/form-data path (bypasses `FetchPort` via FFI)
- Playwright-level network mocking or changes to `webcompy_testing`
