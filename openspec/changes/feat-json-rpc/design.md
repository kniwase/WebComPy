# Design: feat-json-rpc

## Context

Preceding changes provide all the plumbing: `feat-asgi-mount` inserts user/framework ASGI apps into the route table; `ServerFetchPort` makes self-site calls in-process during SSR/SSG with hydration baking; `from_json` (typed-api-client) reconstructs typed values schema-first; `encode_with_meta` (typed-response) produces the metadata sidecar for non-JSON-native types. What remains is a procedure-dispatch layer. JSON-RPC 2.0 is chosen over a bespoke protocol because it is small, fully specified, and tool-compatible.

## Goals / Non-Goals

**Goals:**
- Register Python functions as procedures; call them from browser/SSR with typed params and results.
- Full JSON-RPC 2.0 wire conformance including batch and notifications.
- Secure server-side typed decoding via explicit allowlist — never by wire-provided class names.

**Non-Goals:**
- WebSockets, streaming, OpenAPI generation, fluent proxies, cross-service RPC.

## Decisions

### D1: One endpoint, method registry, standard envelope
The dispatcher is a single ASGI endpoint (Starlette route) mounted at `/_webcompy-rpc` by default (registrable at a custom path via the mount mechanism). A per-app registry maps method names to procedures. Request handling: parse JSON → validate envelope → look up method → decode params → invoke (await if coroutine) → encode result → respond. Batch requests map over entries; notifications (`id` absent) execute without a response body.

**Why a single endpoint**: keeps routing trivial, batches natural, and the attack surface centralized behind one validation path.

### D2: Metadata rides as an extra member, never inside standard members
```json
{"jsonrpc": "2.0", "method": "users.get", "params": {"id": 1}, "id": 1}
{"jsonrpc": "2.0", "result": {...}, "meta": {"result.created": "datetime"}, "id": 1}
```
`meta` uses the `typed-response` format (path→tag map). JSON-RPC 2.0 permits additional members; standard-conformant peers ignore it.

**Why**: embedding metadata inside `params`/`result` would corrupt the argument schema the procedure expects. A sibling member keeps both worlds clean — generic JSON-RPC clients can call procedures with plain JSON.

### D3: Server-side decoding is allowlist-only — the security crux
Hydration decoding trusts server-generated payloads, and typed-response decoding happens client-side. RPC is the first path where the SERVER decodes CLIENT-controlled typed data. Therefore:
- `params` are decoded with `from_json(schema, params, strict=True)`; schemas come from the server-side procedure registration (type annotations of the registered function), never from the request.
- `meta` tags map to the closed restoration set from `typed-response`; dataclass/class restoration from `meta` names is forbidden unless the class was explicitly registered via an allowlist API (reusing the `register_type_handler` concept from transfer-codec, scoped per registry).
- Violations (unknown method, schema mismatch, unregistered type tag) map to JSON-RPC error codes `-32601`/`-32602`.

### D4: Procedures declare schemas by signature
```python
@rpc.procedure
async def get_user(id: int) -> User: ...
```
Param schema derives from the function's type annotations (`inspect.signature` + `get_type_hints`); result schema from the return annotation. Shared dataclasses live in the app package (shipped to the browser), so client and server literally import the same classes.

**Why**: no separate IDL or codegen — the Python signature IS the contract. Validation is structural (from_json strict), not value-constraint based; procedures needing value validation do it in the body (documented).

### D5: Client is a thin typed caller over FetchPort
```python
user = await rpc.call("get_user", {"id": 1}, result_type=User)
```
The client serializes the envelope, posts through `FetchPort` (self-site → in-process during SSR/SSG; transfer cache → hydration bake), then decodes `result` via `from_json` + `meta`. JSON-RPC errors raise a dedicated `RpcError` carrying code/message/data. Batch and notification helpers are provided but the single-call path is the documented default.

### D6: Dispatcher placement reuses the mount mechanism
The dispatcher ASGI app is mounted through the same route-insertion point as user mounts (`feat-asgi-mount`), reserved prefix `/_webcompy-rpc` registered in the CLI spec's endpoint table. The insertion is framework-internal: it bypasses the user-mount collision validation (which rejects `/_webcompy*` prefixes) and is documented by a `cli` delta in this change. Disabled when no procedures are registered (no endpoint added).

## Risks / Trade-offs

- [Signature-derived schemas drift from runtime behavior (e.g. `**kwargs`)] → `**kwargs`/untyped params are rejected at registration time; spec requires fully annotated signatures.
- [Batch requests amplify a validation bug across entries] → each batch entry is validated independently; per-entry errors returned per-entry per JSON-RPC 2.0.
- [Notification execution during SSR could fire-and-forget fetch side effects] → notifications during SSR execute inline (no response expected but work completes before render finishes, via the async scheduler); documented.
- [Allowlist registry becomes a second type system to maintain] → it reuses `register_type_handler` and defaults to the closed tag set; most apps never touch it.
- [Error responses leaking internals] → internal errors return `-32603` with a generic message; details logged server-side only. Spec-mandated.
- [`RpcError` raised inside component setup/render] → participates in the framework error pipeline (`error-handling` spec) with no special handling: catchable by `ErrorBoundary`; during SSG an uncontained error fails the build.

## Migration Plan

None — new capability, off unless procedures are registered.

## Open Questions

- Whether `meta` on requests (client→server metadata for params) is needed beyond the closed tag set — default: supported with the closed set + allowlist; revisit after real usage.
- Exact default mount path (`/_webcompy-rpc` vs `/_webcompy/rpc`) — finalize in implementation; spec uses `/_webcompy-rpc`.
