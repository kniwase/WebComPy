# Proposal: feat-typed-realtime

## Why

`feat-websocket-composable` delivers raw text frames; realtime applications almost always exchange structured messages (dataclasses). WebComPy already owns the serialization stack — schema-driven `from_json` (#237), framework-neutral `encode_with_meta` + body wire mode (#241), and the json-rpc allowlist pattern for safe type-tag decoding (#244) — but none of it is wired into the realtime composables. Without this change, users hand-roll `json.loads`/`from_json` in their pump loops, losing metadata-based type restoration (datetime, UUID, Decimal, custom types) and re-introducing exactly the boilerplate the framework removed elsewhere.

## What Changes

- Additive `message_type` parameter on `use_websocket(url, *, message_type=None, strict=True, ...)`: when set to a dataclass type `T`, the handle becomes an `AsyncIterator[T]` and `.send()` accepts `T` instances.
  - **Receive**: each text frame is parsed as JSON; the `__webcompy_transfer_meta__` body member (typed-response body wire mode) is split off and consumed; the payload is reconstructed via `from_json(T, payload, meta=meta, strict=...)` and yielded as `T`.
  - **Send**: `encode_with_meta(instance, type_handlers=...)` + `merge_meta_into_body` produce the JSON text frame, so the peer can restore metadata-typed fields.
- New `.last_error: Signal[Exception | None]` on typed handles: a frame that fails JSON parsing, schema reconstruction, or type-tag validation is **skipped** (never yielded), surfaced on `.last_error`, and warned — the subscription and connection survive. `strict=True` (default) rejects unknown/mismatched fields, catching schema drift loudly; `strict=False` opts into lenient mode.
- App-scoped realtime type allowlist: `register_realtime_type_handler(cls, encoder, decoder)` (mirroring the json-rpc `register_type_handler` pattern, qualified-name tags, closed builtin tag set) stored in the app DI scope, enabling custom type restoration on both send and receive without module-level globals.
- `message_type` targets SHALL be dataclass types (body wire mode requires a top-level JSON object); non-dataclass targets raise a clear error.
- SSR and hydration behavior unchanged from `feat-websocket-composable` (no transfer of typed messages or errors).

## Capabilities

### New Capabilities

- `typed-realtime`: Typed message send/receive for realtime composables — the `message_type` contract, the wire envelope (body meta member), receive-side schema reconstruction with skip-on-error semantics, the app-scoped realtime type allowlist, and `.last_error` surfacing.

### Modified Capabilities

(none — the typed behavior is specified entirely within `typed-realtime`; it references `use_websocket` from `feat-websocket-composable` in prose only)

## Impact

- **Code**: new `packages/webcompy/src/webcompy/realtime/_typed.py` (typed handle wrapper + allowlist registry); public re-exports. Reuses `webcompy/ajax/_serde.py` (`from_json`), `webcompy/hydration/_transfer_meta.py` (`encode_with_meta`, `merge_meta_into_body`, `META_BODY_KEY`), and the allowlist pattern from `webcompy/rpc/_registry.py`.
- **APIs**: additive only (`message_type`/`strict` parameters, `register_realtime_type_handler`, `.last_error` on typed handles). No breaking changes.
- **Dependencies**: `feat-websocket-composable`; existing `typed-api-client`, `typed-response`, `json-rpc` machinery. No new third-party dependencies.
- **Downstream**: `feat-rpc-websocket` builds its message codec on this wire envelope.
- **Docs**: new Markdown-driven docs page covering typed messages, the allowlist, and error handling.

## Known Issues Addressed

(none)

## Non-goals

- Typed SSE (`use_event_source` with `message_type`) — follow-up change; the wire envelope is defined here so it can be added without redesign.
- Non-dataclass message targets (top-level `list[T]`, scalars) — body wire mode requires a top-level object.
- Schema evolution/versioning negotiation between peers.
- Automatic reconnection replay of missed typed messages (remains the documented gap + refetch recipe).
- Hydration transfer of typed messages or `.last_error`.
