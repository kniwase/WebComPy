# Proposal: feat-rpc-contracts

## Why

RPC calls today are fully dynamic: clients pass method names as strings (`rpc.call("add", ...)`, `RpcWsClient.call("add", ...)`, `subscribe("ticker", ...)`) and both parameters and results are `Any`, so pyright cannot detect calls to nonexistent methods, parameter type violations, or result-type mismatches. WebComPy already holds complete type information for every procedure at registration time, and both sides run Python — so a tRPC-like static-typing experience is achievable without code generation: shared, declarative contract objects that server and browser import from the same dependency-neutral module.

## What Changes

- **BREAKING** Redesigns the RPC registration and client APIs around declarative contracts. The old interfaces are removed outright (no deprecation phase; the framework is pre-1.0 with no users):
  - `app.rpc.register(name, fn)` / `register_subscription(name, fn)` are replaced by `app.rpc.bind(contract, impl)` (single method, auto-dispatching on the contract kind, plus `@app.rpc.bind(contract)` decorator sugar).
  - Module-level `rpc.call` / `rpc.notify` / `rpc.batch` / `rpc.stream` are removed from the public API (internalized as the implementation of `RpcHttpClient`).
  - `RpcWsClient.call` / `notify` / `stream` / `subscribe` stop being the documented client API and are re-designated as the `RpcTransport` protocol surface.
- **New capability `rpc-contracts`**: three contract classes defined in a shared, dependency-neutral schema module (`my_app/rpc_schema.py`) that both environments import:
  - `Procedure("add", AddParams, int)` — one call, one typed result: `await add(client, AddParams(2, 3))` returns `int`. `Procedure` invocation returns an `RpcCall[P, R]` (`Awaitable[R]`) so the same expression works for single calls and for batching (see below).
  - `StreamingProcedure("produce", ProduceParams, Item)` — call-scoped finite stream (assumes `feat-rpc-streaming` is implemented): `produce(client, ProduceParams(2))` returns `RpcStream[Item]`.
  - `Subscription("ticker", TickerParams, Tick, replay_size=256)` — shared infinite event stream: `ticker(client, TickerParams("a"))` returns `RpcSubscription[Tick]`. `replay_size` is declared on the contract (default 256) and flows to the subscription buffer.
  - `RpcCall[P, R]` — public awaitable returned by `Procedure`; `await` performs a single call, passing the call to `batch` defers I/O.
  - `batch(*calls: RpcCall, return_exceptions=False)` — typed batch over HTTP and WebSocket (free function, `from webcompy.rpc import batch`). Calls share one transport round-trip (HTTP: one POST array, WebSocket: one array frame) reusing the existing `dispatch_payload` batch path; heterogeneous batches infer `tuple[R1, ..., Rn]` via 1..6 overloads (gather-style, variadic fallback is `tuple[R, ...]`), `return_exceptions=True` surfaces per-call `RpcError`s as `R | RpcError` entries in input order.
- `Procedure.notify(transport, params)` provides a typed fire-and-forget notification. `batch` applies only to `Procedure` calls; streaming and subscription contracts are rejected.
- `RpcTransport` protocol (`call` / `notify` / `stream` / `subscribe`) is the official transport contract, implemented by `RpcWsClient` (all four) and a new `RpcHttpClient` (call/notify/stream; subscribe raises `RpcError`), which also makes contracts usable during SSR (HTTP bake preserved, including `batch` via the array POST bake).
- `bind` performs registration-time signature validation: parameter annotation, result annotation, and (for subscriptions) yield-type must match the contract's declared types; mismatches and unannotated declarations are rejected. For `Subscription`, `replay_size` from the contract flows to `SubscriptionInfo`. This turns the schema module into the single source of type truth with drift protection.
- pyright then statically checks contract usage: nonexistent contract names are undefined-name errors, `AddParams("x")` is a type error, `await add(...)` is inferred as `int`, `await batch(add(client,p1), get_user(client,p2))` is inferred as `tuple[int, User]`, and `async for` over a subscription is inferred as the event type.
- The JSON-RPC 2.0 wire (HTTP POST + WebSocket frames, batch, notifications, error codes, allowlist decoding, transfer `meta`) and the subscription/stream wire protocols (cursors, replay, rejoin, resync, SSE, `stream_id`) are unchanged; `batch` reuses the existing batch wire.

## Capabilities

### New Capabilities

- `rpc-contracts`: Declarative RPC contract objects (`Procedure`, `StreamingProcedure`, `Subscription`), the `RpcTransport` protocol, `RpcHttpClient`, contract-based binding with registration-time signature validation, and the dependency-neutral schema-module convention.

### Modified Capabilities

- `json-rpc`: Registration moves from `register` to contract binding with signature validation; the public module-level client functions (`call` / `notify` / `batch` / `stream`) are removed and replaced by `RpcHttpClient` per `rpc-contracts`; dispatcher wording follows (endpoint presence is keyed on bound contracts).
- `rpc-websocket`: `RpcWsClient` is re-designated as the WebSocket transport implementing `RpcTransport`; calls, streams, and subscriptions are issued through contracts. Wire behavior (id correlation, in-flight failure, cursors, rejoin/resync, heartbeat, reserved methods, SSR no-op) is unchanged.
- `rpc-streaming`: Streaming procedures register via `bind` with a `StreamingProcedure` contract (detection and validation rules unchanged); streaming calls are issued through contracts. The SSE/WS wire and `RpcStream` semantics are unchanged.
- `cli`: Wording update — the `/_webcompy-rpc` dispatcher endpoint is exposed when one or more RPC contracts are bound.

## Impact

- **Code**: new `webcompy/rpc/_contracts.py` (contract classes + `RpcCall` + `RpcTransport` + `RpcHttpClient` + `batch` with 1..6 overloads and `return_exceptions`, HTTP/WS dispatch); `webcompy/rpc/_registry.py` (bind + validation including `Subscription(replay_size)`, remove `register`/`register_subscription`); `webcompy/rpc/_client.py` (internalized module functions); `webcompy/rpc/_ws_client.py` (transport re-designation + WS batch array-frame handling, no other wire changes); `webcompy/rpc/__init__.py` exports; `webcompy_cli/_server.py` wording only. Server dispatcher/endpoints unchanged (batch wire already supported).
- **Tests**: all `tests/test_rpc_*.py` files (8 files) are migrated to contract-based usage; new unit tests for bind validation and contract delegation.
- **E2E**: `e2e/core/my_app/app.py` (bind + contracts), `pages/rpc_ws.py` (contract usage), and any streaming E2E added by `feat-rpc-streaming`.
- **Docs**: new `rpc_contracts.md` document; `rpc_websocket.md` (and `rpc.md` if present) rewritten to contract usage; review-knowledge tables updated; retired API names added to the `check-doc-spec-refs.py` blocklist.
- **Dependencies**: `feat-sse-post` (`0d65127e`) and `feat-rpc-streaming` (`7e029e69`) are implemented and merged into the base branch (completed). No new third-party dependencies.

## Known Issues Addressed

(none)

## Non-goals

- No code generation of any kind — contracts are hand-written runtime objects with static generics (PEP 695).
- No per-parameter call syntax (`add(client, a=2, b=3)`) — parameters are passed as a single typed dataclass object.
- No changes to the JSON-RPC 2.0 wire protocol, transfer `meta` codec, subscription rejoin/replay/resync semantics, or the `RpcStream` / `RpcSubscription` handle objects (batch reuses the existing batch wire).
- No `use_rpc` composable or DI-injected default transport — transports are passed explicitly to contracts (and to `RpcCall` via the originating `Procedure` call).
- No changes to `register_type_handler` (the type allowlist stays as-is).

## Explicitly Excluded

Any of the following is a review failure — the change is intentionally breaking with no compat layer:

- `DeprecationWarning` / `PendingDeprecationWarning` or `warnings.warn` for `register` / `call` / `notify` / `stream`
- Alias or shim: `register = bind`, `register_subscription = bind`, `procedure = bind`, `call = Procedure(...).__call__`, `webcompy/rpc/_compat.py`, or `__getattr__` fallback in `webcompy/rpc/__init__.py` that re-exports old names
- Old tuple-based batch overload: `batch(calls: Sequence[tuple[str, ...]])` or `batch([("add", ...)])` or any `*args` that accepts `str` method names
- Legacy param decode path: array-form `params` mapping to dataclass fields (contract-bound procedures must hard answer `-32602`)
- `replay_size` compat kwarg on `register_subscription` (must only flow from `Subscription(replay_size=...)`)
- Migration guide file (`docs/rpc_migration.md`, `MIGRATION.md` section, or `docs_app` breadcrumb "Legacy RPC")
- Docs showing both APIs side-by-side ("old way vs new way")
- `if hasattr(app.rpc, "register"):` fallback branches in tests or `e2e`
- Renaming `register_type_handler` (it stays; see tasks 8.3 blocklist caveat)
