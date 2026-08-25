# Design: feat-fetch-rpc-middleware

## Context

Two independent interception needs converge on the same mechanism: production cross-cutting concerns (auth headers, tracing, retries) around `FetchPort.fetch`/`stream` and the HTTP JSON-RPC client, and browser-side test doubles (mocks) that today are impossible because `webcompy_testing` is CPython-only and excluded from the browser wheel.

Current state on `origin/main`:

- `FetchPort.fetch(url, *, method, headers, body) -> Response` and `.stream(...) -> FetchStream` (`ports/_fetch.py`). All HTTP traffic funnels through `inject(FETCH_PORT_KEY)` — `HttpClient.request` (`ajax/_fetch.py:277`), `_post_envelope`/`_stream_impl` (`rpc/_client.py:73,194`), SSE fetch (`realtime/_sse.py`), resource fallback (`ports/_browser/_resource.py:49`). Note: since upstream #280, `body` accepts `str | bytes | None` and `HttpClient(form_data=...)` is routed through the port as a multipart body (previously an FFI bypass), so fetch middleware intercepts multipart submissions too.
- The RPC client has **no per-call header API**: `_post_envelope` hardcodes `headers={"Content-Type": "application/json"}` (`rpc/_client.py:70`, also `:222` for streams). Validation lives solely in `_resolve_single` (`rpc/_client.py:43`: `apply_transfer_meta` + `from_json`) and `_decode_stream_item` (`rpc/_stream.py`) for streams.
- DI is last-wins per key (`di/_scope.py:38`); no priority/order fields anywhere. Plugins register in `AppConfig.plugins` declaration order; `PluginManager.init_render_context` runs **after** `_register_ports()` (guaranteed by `port-provisioning` spec), so plugins can override ports.
- Hydration coupling: `BrowserFetchPort.populate_from_transfer` seeds the response cache from the SSR payload; `ServerFetchPort.get_transfer_data` exports self-site responses for hydration. Any wrapper must delegate these or hydration breaks.
- `ServerFetchPort._is_blocked` prevents SSR recursion; wrappers must not bypass it (safe as long as middleware calls `next`, which invokes the inner port).

## Goals / Non-Goals

**Goals:**

- Two independent middleware systems: `FetchMiddleware(request, next) -> Response` and `RpcMiddleware(ctx, next) -> Any`, both stackable, with `middlewares[0]` outermost.
- Interception without losing guarantees: `next(request, response=...)` / `next(ctx, response=...)` short-circuits the network while keeping downstream processing (hydration cache semantics at fetch layer; `_resolve_single` validation at RPC layer).
- Additive registration via DI registries, declarative plugin hooks, and utility functions.
- Streaming supported: `next` resolves when headers are committed and body consumption has not started.

**Non-Goals:** WebSocket middleware; interception of the `HttpClient` `form_element` path (a browser-only DOM-node submission that bypasses `FetchPort` via FFI; note that `form_data=` multipart bodies ARE routed through `FetchPort` since upstream #280 and therefore are interceptable); per-procedure registration; changes to `webcompy_testing`.

## Decisions

### 1. Two separate middleware types over one generic chain

`FetchMiddleware` sees raw HTTP (`url/method/headers/body` → `Response`/`FetchStream`); `RpcMiddleware` sees typed procedure calls (`method/params/headers/result_type` → result). RPC middleware headers are threaded down into the fetch layer's header dict.

- **Why two**: RPC args live in typed dataclasses before `encode_with_meta`; a single raw-HTTP middleware would bury them in a JSON string and make arg-level substitution impossible. Conversely fetch middleware must exist independently because non-RPC callers (`HttpClient`, SSE, resources) need it too.
- **Rejected**: one unified pipeline at `FetchPort` only — loses typed args; one at `RpcTransport` only — leaves `HttpClient` unextensible.

### 2. Registries provided via DI (A), plugin hooks as sugar (B), utilities (C)

- `FETCH_MIDDLEWARE_KEY = InjectKey[FetchMiddlewareRegistry]("webcompy-fetch-middleware")` and `RPC_MIDDLEWARE_KEY = InjectKey[RpcMiddlewareRegistry]("webcompy-rpc-middleware")`. Registry objects expose `use(middleware)` (append), `middlewares` (read-only snapshot list), and are created fresh per `RenderContext` by `_register_ports()` — satisfying render-context isolation (no app-level mutable global).
- `WebComPyPlugin.get_fetch_middlewares() -> list[FetchMiddleware]` / `get_rpc_middlewares() -> list[RpcMiddleware]` — new default-empty hooks. `PluginManager.init_render_context` concatenates hook results **in declaration order** and calls `registry.use(...)` for each, after static providers but before chain assembly.
- `add_fetch_middleware(mw)` / `add_rpc_middleware(mw)` module functions inject the active registry and delegate to `use()`.
- **Why A primary**: plugins are not the only source (tests, app code can `inject(registry).use(...)`). B stays consistent with `get_scripts()` precedent (`plugin/_manager.py` aggregates in declaration order) and gives plugin authors an obvious, non-confusable path distinct from `get_providers`.

### 3. Chain assembly point and ordering

Assembly runs once per `RenderContext`, immediately after `app._plugin_manager.init_render_context(self)` inside `RenderContext.__init__` (after `_register_ports()`), re-providing `FETCH_PORT_KEY` with the wrapped chain:

```python
inner = di_scope.inject(FETCH_PORT_KEY)
for mw in reversed(registry.middlewares):
    inner = _MiddlewareFetchPort(inner, mw)
di_scope.provide(FETCH_PORT_KEY, inner)
```

- Ordering contract: `middlewares[0]` is outermost (first to see the request, last to see the response); `reversed` composition implements this. Matches Django/aiohttp/Express convention of declaration order = execution order.
- Assembly after plugins means a plugin that replaces the whole port becomes the chain's innermost layer (middleware still wraps it) — documented behavior.
- Lazy alternative rejected: wrapping every `inject(FETCH_PORT_KEY)` call site adds branching to hot paths and makes ordering harder to reason about; eager assembly keeps a single deterministic composition point. Child-scope additions after assembly are out of scope (documented).
- RPC side: `_call_impl` / `_notify_impl` / batch HTTP path resolve `RPC_MIDDLEWARE_KEY`'s registry and wrap the transport invocation per call via the same reversed composition; headers from middleware ctx merge onto `{"Content-Type": "application/json"}` (Content-Type forced back after merge).

### 4. Interceptor escape hatch keeps validation

- Fetch layer: returning without `next`, or calling `next(request, response=synthetic_response)`, skips the inner port. Synthetic responses at this layer remain safe: RPC callers still run `json_loads` + `_resolve_single` on them.
- RPC layer: `next(ctx, response={"result": ..., "meta": ...})` short-circuits `_post_envelope` but the chain runner feeds the synthetic fragment through the same `_resolve_single(result_type, ...)` path (and `_decode_stream_item` for streams), preserving `apply_transfer_meta` + `from_json` guarantees. Returning a bare value without `next` is **not** supported (would bypass validation); the runner documents this.
- Batch: middleware wraps the batch dispatch as a whole (`ctx.is_batch=True`, `ctx.batch_entries=[(method, params, result_type), ...]`) — per-entry validation stays in the existing batch resolution loop; a synthesized `response=` list is resolved positionally against those entries.
- Streaming (fetch): `await next(request)` resolves to a `FetchStream` once headers/status are committed, before body consumption; interceptors may substitute a stream and downstream consumption still applies.
- Streaming (RPC): `_stream_impl` is synchronous and pumps inside a background task, so the RPC middleware chain for streams executes when the pump task starts (`_setup_and_pump`). `next` therefore resolves at header-commit time, matching the contract, but middleware side effects occur later than for `call`/`notify`. Substitution uses `next(ctx, stream=synthetic)`; per-item decoding (`_decode_stream_item`) is unchanged.
- Normalization: `_resolve_single` requires `jsonrpc == "2.0"`, so the chain runner normalizes a synthesized fragment via `{"jsonrpc": "2.0", **fragment}` before validation. Middleware authors write only `{"result": ..., "meta": ...}`.

### 5. Wrapper delegation contract

`_MiddlewareFetchPort` delegates `populate_from_transfer`, `get_transfer_data` (server), `clear_cache`, `close`, `is_self_site_url`, and `noop` to the innermost concrete port so hydration transfer, blocked-path guards, and SSE degradation keep working unchanged. Middleware never receives these internal methods.

### 6. Late registration via generation counter

A browser app lives in a single render context for its lifetime, so an eagerly assembled chain would freeze out later registrations. The fetch wrapper is instead installed **always** (even with zero middlewares) and consults a monotonically increasing `generation` counter on the registry: `use()` bumps the counter and the wrapper rebuilds its cached sub-chains only when the counter changed — one integer comparison per request on the steady-state path. RPC middleware reads the registry snapshot at each operation, so late registration is naturally effective there. This supersedes the earlier "zero-wrapper fast path" idea (which would have made post-boot registration inert).

## Risks / Trade-offs

- [Always-wrap adds a per-request generation check] → Single integer comparison on the steady-state path; sub-chains are rebuilt only when the registry changes.
- [Plugin replaces FETCH_PORT_KEY entirely, dropping middleware] → Assembly runs last, so replacement becomes innermost; middleware still applies. Whole-port replacement + middleware interplay documented.
- [`Content-Type` clobbered by middleware] → Runner forces `application/json` after merging user headers.
- [Synthetic RPC fragments malformed] → `_resolve_single` raises `RpcError(INTERNAL_ERROR/SERVER_ERROR)`; unit tests cover error surfacing.
- [Order confusion] → Spec states `middlewares[0]` outermost with a worked example; composition code uses `reversed` in one shared helper for both systems.
- [Stream close/cancel propagation] → Wrapper delegates `close()/aclose()` to inner stream; tested.

## Migration Plan

Purely additive; no existing call sites change behavior when no middleware is registered (the always-installed wrapper performs only a generation comparison and delegates everything to the inner port). Rollback = revert. Specs synced at archive.

## Open Questions

None blocking. Naming confirmed (`FetchMiddleware` / `RpcMiddleware`); ordering confirmed (`[0]` outermost).
