# Spec: rpc-middleware

## ADDED Requirements

### Requirement: RpcMiddleware shall wrap HTTP JSON-RPC operations with a next function

`RpcMiddleware` SHALL be an async callable receiving a context exposing `method: str`, `params: Any` (the typed dataclass before encoding), mutable `headers: dict[str, str]`, and `result_type`, plus a `next` function. The middleware SHALL apply to `call`, `notify`, `batch`, and streaming calls over the HTTP transport. WebSocket transports SHALL NOT be intercepted.

#### Scenario: Typed params visible before encoding

- **WHEN** `await add(transport, AddParams(a=1, b=2))` is invoked with a registered middleware
- **THEN** the middleware's `ctx.params` is the `AddParams` instance (not a JSON string)

### Requirement: Middleware may mutate args and headers before next

Middleware MAY replace `ctx.params` or mutate `ctx.headers` before calling `next(ctx)`; the mutated values SHALL be used for envelope encoding and merged into the fetch-layer request headers respectively. Merged headers SHALL be combined onto the fixed transport headers with `Content-Type: application/json` preserved regardless of middleware mutations.

#### Scenario: Header injection reaches the wire

- **WHEN** middleware sets `ctx.headers["Authorization"] = "Bearer t"`
- **THEN** the underlying `FetchPort.fetch` receives headers containing both `Authorization` and `Content-Type: application/json`

#### Scenario: Params substitution

- **WHEN** middleware replaces `ctx.params` with a new dataclass instance matching the procedure contract
- **THEN** the encoded envelope carries the substituted values

### Requirement: Scoping shall be expressed via context metadata inside middleware

There SHALL be no per-procedure registration API; middlewares SHALL inspect `ctx.method` (and other context fields) to decide whether to act. Batch dispatches SHALL expose batch-level metadata on the context so middleware can distinguish them from single calls.

#### Scenario: Selective application

- **WHEN** a middleware only acts when `ctx.method == "add"` and another method is called
- **THEN** the other call passes through unchanged

### Requirement: Synthesized results shall keep validation guarantees

A middleware MAY short-circuit by calling `next(ctx, response={"result": ..., "meta": ...})`. The chain runner SHALL feed the synthesized fragment through the same result-resolution path as network responses (`apply_transfer_meta` then schema decoding against `ctx.result_type`) so meta decoding and type validation are never bypassed. Returning a bare value without calling `next` SHALL not be supported.

#### Scenario: Mocked procedure result validated

- **WHEN** middleware short-circuits `add` via `next(ctx, response={"result": 3})`
- **THEN** the caller receives the value decoded through the same validation path as a server response

#### Scenario: Malformed synthesis surfaces as RPC error

- **WHEN** middleware synthesizes a result that fails schema validation for `ctx.result_type`
- **THEN** the caller receives an `RpcError` consistent with invalid-schema responses

### Requirement: Registries, plugin hooks, and utilities shall mirror the fetch system

`RPC_MIDDLEWARE_KEY` SHALL resolve to a per-render-context registry with additive `use(middleware)`. `WebComPyPlugin.get_rpc_middlewares()` SHALL aggregate in declaration order onto that registry. `add_rpc_middleware(mw)` SHALL delegate to it. Ordering SHALL match the fetch system: registered order applies with `middlewares[0]` outermost.

#### Scenario: Declaration-order aggregation

- **WHEN** plugins `[first, second]` each declare RPC middlewares
- **THEN** `first`'s middleware sits outermost relative to `second`'s

### Requirement: Streaming RPC shall support interception at stream start

On SSE streaming calls, middleware `next` SHALL resolve once the stream is opened — status/headers committed, items not yet consumed — and interceptors MAY substitute the stream. Per-item decoding of streamed results SHALL continue to apply after interception.

#### Scenario: Stream interception preserves item decoding

- **WHEN** middleware substitutes a synthetic item stream
- **THEN** each consumed item still flows through the standard stream-item decoding path
