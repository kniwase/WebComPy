# Proposal: feat-json-rpc

## Why

`feat-typed-api-client` + `feat-asgi-mount` cover calling conventional HTTP APIs with typed clients. But for APIs built specifically for a WebComPy app, a procedure-call model is a better fit than hand-designing REST resources: define a Python function server-side, call it from the browser with typed arguments and results. Because both sides run Python and share modules via the app wheel, procedures can share dataclass schemas directly. Building on the JSON-RPC 2.0 standard (instead of a bespoke protocol) gives batching, notifications, standard error codes, and interoperable tooling for free.

## What Changes

- New JSON-RPC 2.0 dispatcher: a Starlette endpoint (intended mount point: `/_webcompy-rpc` or a user-chosen path via the `feat-asgi-mount` mechanism) plus a server-side procedure registry. Procedures are plain Python functions (sync or async) registered by name.
- Full JSON-RPC 2.0 conformance: `jsonrpc`/`method`/`params`/`id` envelope, positional and named params, batch requests, notifications, and the standard error codes (`-32700` parse error, `-32600` invalid request, `-32601` method not found, `-32602` invalid params, `-32603` internal error).
- One sanctioned extension: an optional `meta` member alongside `params`/`result` carrying transfer metadata in the `typed-response` wire format, enabling typed restoration of non-JSON-native values. The extension never alters standard members, so generic JSON-RPC clients can still call procedures (metadata simply goes unused or unproduced).
- Type safety with a strict security boundary: params and results deserialize via `from_json` (strict mode server-side) against per-procedure registered schemas. Type restoration from `meta` uses an explicit **allowlist registry** (reusing `register_type_handler`-style registration): the server SHALL NOT resolve classes from client-controlled names. This change is the only place where the server decodes client-controlled typed payloads, and the allowlist is mandatory there.
- Browser client: `rpc.call("method", params, result_type=T)` (or generated thin wrappers) going through `FetchPort` — so SSR/SSG calls dispatch in-process via ASGI transport and results are baked into hydration payloads like any self-site fetch; `transfer=False` opt-out applies.

## Capabilities

### New Capabilities

- `json-rpc`: JSON-RPC 2.0 dispatcher, procedure registry, metadata extension, allowlist type decoding, and the typed browser client.

### Modified Capabilities

- `cli`: The server route table gains a framework-internal JSON-RPC dispatcher endpoint at the reserved prefix `/_webcompy-rpc` (present only when procedures are registered; inserted via the mount route-insertion point but exempt from user-mount collision validation).

## Impact

- **Code**: new module `packages/webcompy-server/src/webcompy_server/rpc/` (dispatcher + registry), browser client in `packages/webcompy/src/webcompy/ajax/` or `webcompy/rpc/`, wiring for the official mount point.
- **APIs**: new public APIs (`register_procedure`/decorator, `rpc.call`).
- **Dependencies**: none.
- **Implementation order**: Builds on `feat-asgi-mount` (mount route-insertion point), `feat-typed-api-client` (`from_json`), and `feat-typed-response` (`encode_with_meta` / `meta` wire format); those changes MUST be implemented first.
- **Specs**: new `json-rpc`; delta to `cli`.

## Known Issues Addressed

(none)

## Non-goals

- WebSocket transport or server-initiated calls (JSON-RPC over HTTP POST only).
- Auto-generated OpenAPI documentation for procedures (JSON-RPC is not REST; tooling is out of scope).
- Chained/fluent client proxies (same deferral as `feat-typed-api-client`).
- Cross-service RPC (the dispatcher serves the same-process app; external exposure is possible but not a design target).
- Streaming responses.
