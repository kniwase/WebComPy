# Design: feat-rpc-contracts

## Context

The RPC layer has four pieces: a `ProcedureRegistry` (`webcompy/rpc/_registry.py`, `ProcedureInfo`/`SubscriptionInfo`, `register`/`register_subscription`), a transport-neutral dispatch core + bare ASGI dispatcher (`webcompy_server/rpc/_dispatcher.py`), a WS endpoint with a `SubscriptionHub` and (after `feat-rpc-streaming`) a `StreamCallHub`, and clients: module-level `rpc.call`/`notify`/`batch`/`stream` over `FetchPort` (`webcompy/rpc/_client.py`) plus `RpcWsClient` (`webcompy/rpc/_ws_client.py`). After `feat-rpc-streaming`, `ProcedureInfo` carries `is_streaming` and generator-based element-type extraction, and `RpcStream` handles call-scoped streams on both transports.

Everything is fully dynamic today: method names are strings, params/results are `Any`, so pyright cannot catch nonexistent methods, wrong parameter types, or result misuse. Both sides run Python 3.12+ and the registry already extracts complete type metadata at registration — the missing piece is a shared, dependency-neutral surface that both environments import. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**

- Declarative contract objects (`Procedure` / `StreamingProcedure` / `Subscription`) that are the single source of RPC type truth, importable from both browser and server.
- tRPC-level static checking with pyright: contract-name existence, parameter types, result inference, and event-type inference.
- Registration-time signature validation (`bind`) so schema modules cannot drift from implementations.
- One transport protocol (`RpcTransport`) with two conforming transports: `RpcWsClient` (browser, realtime) and `RpcHttpClient` (browser + SSR with HTTP bake).
- Full removal of the old string-based APIs (no deprecation).

**Non-Goals:**

- No code generation; no per-parameter call syntax; no `use_rpc` composable; no changes to wire protocols (batch reuses the existing batch wire), codecs, `RpcStream`, `RpcSubscription`, or `register_type_handler`.

## Assumptions

- `feat-sse-post` (`0d65127e`) and `feat-rpc-streaming` (`7e029e69`) are implemented and merged into the base branch (rebase completed at `ded3285f`; validation confirmed no title drift).
- The `rpc-streaming` capability's requirement titles match those in the committed delta after its archive (verified).

## Decisions

### 1. Three contract classes, one shared schema module

```python
# my_app/rpc_schema.py — imports ONLY client-safe webcompy core
from dataclasses import dataclass
from webcompy.rpc import Procedure, StreamingProcedure, Subscription

@dataclass
class AddParams: a: int; b: int = 0

add = Procedure("add", AddParams, int)

@dataclass
class ProduceParams: n: int
@dataclass
class Item: n: int

produce = StreamingProcedure("produce", ProduceParams, Item)

@dataclass
class TickerParams: ticker_id: str
@dataclass
class Tick: seq: int

ticker = Subscription("ticker", TickerParams, Tick)
```

- `Procedure[P, R]` — `__call__(transport, params: P) -> RpcCall[P, R]` (sync, returns an `Awaitable[R]`; `await` performs the call). `notify(transport, params: P) -> None` (async, fire-and-forget, not batchable).
- `StreamingProcedure[P, T]` — `__call__(transport, params: P) -> RpcStream[T]` (returns the handle, not awaitable; `RpcStream` supports `async with`).
- `Subscription[P, E]` — `__call__(transport, params: P) -> RpcSubscription[E]`; constructor is `Subscription(name, params_type, event_type, replay_size=256)` with `replay_size: int >=1, bool rejected`, flowing to `SubscriptionInfo`.
- `RpcCall[P, R]` — public awaitable (`__await__`) capturing `name/params/result_type/transport` without I/O until awaited; also the element type for `batch`. `isinstance(call, RpcCall)` is the batch gate (streaming/subscription handles are rejected).
- Unified `__call__` style (no `.subscribe()` verb on contracts).
- Contracts are plain runtime objects whose constructor stores `name`, `params_type`, `result_type`/`event_type` (no reliance on `__orig_class__`). PEP 695 generics (`class Procedure[P, R]`) give pyright the static typing; the runtime payload is the same explicit types, so runtime and static behavior cannot disagree.
- Contract constructors validate: name must be a non-empty `str` not starting with `_webcompy.` (reserved, mirroring the registry rule), `params_type` must be a dataclass type (non-dataclass SHALL be rejected), the type arguments must be `type` instances, and `Subscription` additionally validates `replay_size` (`int` `>=1`, `bool` rejected).

Rationale: contracts must be creatable outside any app/DI context (schema modules are imported at module level), so all validation happens at construction and at `bind` — never lazily on first call.

### 2. Delegation: contracts are pure typed pass-throughs via RpcCall

`Procedure.__call__` does not perform I/O; it captures the call as an `RpcCall`:

```python
class RpcCall[P, R]:
    def __await__(self) -> Generator[Any, None, R]:
        return (yield from self._transport.call(self._name, self._params, result_type=self._result_type))

class Procedure[P, R]:
    def __call__(self, transport: RpcTransport, params: P) -> RpcCall[P, R]:
        return RpcCall(self._name, params, self._result_type, transport)
```

`await add(client, p)` delegates to `transport.call`; `await batch(c1, c2)` delegates to the single-array batch path without re-encoding per-call. All encoding (`encode_with_meta` over dataclass params), `meta` handling, and decoding (`from_json`) stay in the transport layer exactly as today (`_encode_params` / `_resolve_single` / `RpcSubscription._deliver`). Contracts contain no serialization logic, so they need no DI scope and work identically in browser and server. A single `await` of the same `RpcCall` instance is supported; awaiting the same instance a second time SHALL raise `RuntimeError` (`RpcCall already awaited`).

### 3. `RpcTransport` protocol and the two transports

```python
class RpcTransport(Protocol):
    async def call(self, method: str, params: Any = None, *, result_type: Any = None) -> Any: ...
    async def notify(self, method: str, params: Any = None) -> None: ...
    def stream(self, method: str, params: Any = None, *, result_type: Any = None) -> RpcStream[Any]: ...
    def subscribe(self, method: str, params: Any = None, *, event_type: Any = None) -> RpcSubscription[Any]: ...
```

- `RpcWsClient` implements all four (existing behavior; re-designated as transport).
- `RpcHttpClient` (new, in `webcompy/rpc/_contracts.py`) implements `call`/`notify`/`stream` by delegating to the internalized `_client.py` helpers, preserving SSR in-process dispatch and hydration bake for `call`/`notify`, and the `rpc-streaming` SSR degradation for `stream`. Its `subscribe` raises `RpcError` (subscriptions are WebSocket-only).
- A single protocol keeps contract code simple; `RpcHttpClient.subscribe` failing at runtime is acceptable because subscription contracts over HTTP are a type-legal but runtime-invalid combination documented in the spec.

### 4. `bind`: single method with decorator sugar and 3-way validation

```python
app.rpc.bind(add, _add)          # _add(p: AddParams) -> int
app.rpc.bind(ticker, _ticker)    # _ticker(p: TickerParams) -> AsyncIterator[Tick]

@app.rpc.bind(produce)
async def _produce(p: ProduceParams) -> AsyncIterator[Item]: ...
```

- `bind(contract, impl=None)`: with `impl` given it registers immediately; without it it returns a decorator. Contract kind is detected via `isinstance` against the three contract classes.
- Validation uses the existing `_extract_signature` machinery (annotations, order, defaults) plus:
  - `Procedure`: impl must NOT be a generator function; it must take exactly one parameter whose annotation equals `params_type`; its return annotation must equal `result_type`. Iterable-annotated non-generator functions are rejected (matching `feat-rpc-streaming`'s ambiguity rule).
  - `StreamingProcedure`: impl must be a generator function with a subscripted `AsyncIterator[T]`/`AsyncIterable[T]` (async generator) or `Iterator[T]`/`Iterable[T]` (sync generator) return annotation; the element type must equal the contract's `result_type`. This reuses the `feat-rpc-streaming` detection logic; unsubscripted, wrong-kind, and mismatched element types are rejected.
  - `Subscription`: impl must be an async generator function whose return annotation is subscripted `AsyncIterator[T]` (or `AsyncGenerator[T, None]`); `T` must equal the contract's `event_type`. Unannotated or `object`/`Any` element types are rejected (strict; existing `-> object` declarations are migrated as part of the breaking change).
  - `Subscription` `replay_size` validation: `Subscription(replay_size)` is `int` `>=1` (`bool` rejected); `bind` flows `contract.replay_size` into `SubscriptionInfo`/`_Stream` deque `maxlen` (overwrites any prior default).
 - Name collisions across procedures/subscriptions and reserved `_webcompy.*` names are rejected as today.
 - `register` and `register_subscription` and the `procedure` decorator are removed with no alias, `__getattr__` fallback, or deprecation shim. `register_type_handler` is retained. `ProcedureRegistry` gains `bind`; `has_procedures` semantics are unchanged (bound contracts gate endpoint mounting).
- The registered `ProcedureInfo` continues to derive from the implementation's own annotations (as today), so the dispatcher's decode path is untouched; validation guarantees the annotations agree with the contract.

### 5. Schema-module dependency discipline

Contract modules live inside the app package (which is already shipped to the browser bundle) and SHALL import only client-safe core (`webcompy.rpc`, `dataclasses`, `typing`, sibling schema modules). Server-only modules (importing `webcompy_server`, Starlette, or third-party server libraries) SHALL NOT be imported by schema modules — implementations live in separate server-only modules that import the schema module and bind. This is a review-level invariant (the `webcompy-review` skill checks it); the existing dependency resolver already walks app-package imports, so violations surface as bundle failures.

### 6. SSR semantics

- `Procedure`/`StreamingProcedure`/`Subscription` contracts are environment-agnostic; behavior is determined by the transport passed in.
- `RpcHttpClient.call`/`notify` during SSR/SSG use the existing in-process ASGI dispatch and hydration bake (`transfer=False` opt-out as today).
- `RpcWsClient` in SSR keeps its warning + no-op; `RpcHttpClient.stream` in SSR returns the empty finished stream per `feat-rpc-streaming`.
- No contract state is transferred in the hydration payload.

### 7. RpcCall and batch (1..6 overloads, return_exceptions, HTTP/WS)

```python
# webcompy/rpc/_contracts.py — free function, transport-agnostic
@overload
async def batch(call1: RpcCall[Any, R1], *, return_exceptions: Literal[False] = False) -> tuple[R1]: ...
@overload
async def batch(call1: RpcCall[Any, R1], call2: RpcCall[Any, R2], *, return_exceptions: Literal[False] = False) -> tuple[R1, R2]: ...
# ... up to 6 heterogeneous overloads (gather-style)
@overload
async def batch(*calls: RpcCall[Any, R], return_exceptions: Literal[False] = False) -> tuple[R, ...]: ...
@overload
async def batch(call1: RpcCall[Any, R1], *, return_exceptions: Literal[True]) -> tuple[R1 | RpcError]: ...
# ... return_exceptions=True overloads mirror the above with R|RpcError
async def batch(*calls: RpcCall[Any, Any], return_exceptions: bool = False) -> tuple[Any, ...]: ...
```

- **Awaitable gate**: `Procedure.__call__` returns `RpcCall` synchronously; `batch` accepts only `RpcCall` (via `isinstance`). `StreamingProcedure`/`Subscription` handles are rejected (`RpcError`). Awaiting the same `RpcCall` a second time raises `RuntimeError`; `batch` consumes the call without prior await.
- **Single round-trip**: `batch` collects `(name, params, result_type, transport)` from each `RpcCall`, validates all share the same transport instance (mixed transports → `RpcError`), then delegates: `RpcHttpClient` → one `POST` with JSON array via `_post_envelope` (single hydration bake entry), `RpcWsClient` → one array text frame with N `Future`s correlated by `id` (reuses the existing `dispatch_payload` batch wire; `_reader` splits the array response and `close`/`_fail_in_flight` handle N futures on disconnect). At least one call is required (`RpcError` if empty). Streaming-procedure entries are not batchable and are rejected before transport (matches `dispatch_payload(in_batch=True)` but fails fast). `batch` accepts only `RpcCall` instances; a future `RpcCall` that wraps a streaming `ProcedureInfo` (should never happen) is rejected at call time.
- **Import discipline**: `webcompy/rpc/_contracts.py` is the leaf (no top-level import of `ProcedureRegistry` or `RpcWsClient`); `ProcedureRegistry.bind` lazy-imports `Procedure`/`StreamingProcedure`/`Subscription` inside the method, and `batch` lazy-imports `RpcWsClient`/`RpcHttpClient` inside the function to avoid cycles. `_contracts.py` SHALL NOT import `webcompy_server`.
- **SSR bake for batch**: `batch` via HTTP uses the same `FetchPort` path as single calls; the array body is a single cache key `POST:/_webcompy-rpc:[...]` and is recorded via `ServerFetchPort.get_transfer_data` → `BrowserFetchPort.populate_from_transfer` (single entry). Batched calls have no per-entry `transfer` flag (always baked).
- **Error policy**: `return_exceptions=False` (default) raises the first per-call `RpcError` (like `gather(return_exceptions=False)`); `return_exceptions=True` returns `tuple[R|RpcError, ...]` in input order without raising.
- **Typing**: 1..6 heterogeneous overloads give `tuple[R1, R2, ...]` inference (mirrors `asyncio.gather` in `typeshed`); variadic fallback is `tuple[R, ...]`. Implemented in `webcompy/rpc/_contracts.py` with `typing.overload` and `Literal`.

### 8. Naming rationale

- `Procedure` / `StreamingProcedure` / `Subscription` for contracts; `RpcStream` / `RpcSubscription` remain the runtime handle names (owned by `rpc-streaming` and `rpc-websocket` respectively). The `Rpc` prefix marks runtime handles; unprefixed names mark the declarative contracts users write.
- `StreamingProcedure` (not `StreamProcedure`) was chosen for readability; `Subscription` (not `EventStream`) because `feat-rpc-streaming` already defines `RpcStream` for call-scoped streams and the contract/handle pairing `Subscription` → `RpcSubscription` reads naturally.

## Risks / Trade-offs

- **[Risk] The committed `rpc-streaming` delta cannot validate until that capability exists in `openspec/specs/`** → Mitigation: one-time validation exception at proposal commit time (authorized); precondition task 0.2 re-validates after the `feat-rpc-streaming` merge and fixes any title drift before implementation.
- **[Risk] Breaking change ripples through 8 test files (~2500 lines), E2E pages, and docs** → Mitigation: dedicated migration tasks; wire-level tests remain valid because the wire is unchanged; rollback is a revert of one commit.
- **[Risk] pyright inference limits around PEP 695 instance generics** → Mitigation: types are inferred from constructor arguments (well-supported), not from `__orig_class__`; typed usage in tests/E2E exercises inference in CI.
- **[Risk] Hand-maintained schema modules can drift from server implementations** → Mitigation: `bind`-time validation rejects mismatches at registration; drift becomes a startup error, not a runtime decode failure.
- **[Trade-off] Params as a single object (no per-argument syntax)** → deliberate; dataclasses already flow through `encode_with_meta`/`from_json` with full fidelity.

## Migration Plan

Breaking, single-step: remove `register`/`register_subscription` and the module-level client functions; add contracts + `bind` + `RpcHttpClient`; migrate tests, E2E, and docs in the same change. No compatibility shims.

## Explicitly Excluded

See `proposal.md` Explicitly Excluded — no `DeprecationWarning`, alias, shim, `_compat.py`, `__getattr__` fallback, old tuple `batch`, legacy array decode, `replay_size` compat kwarg, migration guide, side-by-side docs, `hasattr` fallback, or `register_type_handler` rename. Any such artifact is a review failure.

## Open Questions

(none)
