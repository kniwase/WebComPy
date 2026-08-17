# Design: feat-typed-realtime

## Context

`feat-websocket-composable` delivers raw `str` frames. The serialization stack already exists and is verified in the codebase:

- `from_json(cls, data, *, strict=False, meta=None)` (`webcompy/ajax/_serde.py`) — schema-driven reconstruction from annotations, never from wire content.
- `encode_with_meta(value, *, type_handlers=None) -> (json_data, meta)` and `merge_meta_into_body(json_data, meta)` with `META_BODY_KEY = "__webcompy_transfer_meta__"` (`webcompy/hydration/_transfer_meta.py`) — framework-neutral metadata encoding; body wire mode requires a top-level JSON object.
- `ProcedureRegistry.register_type_handler(cls, encoder, decoder)` (`webcompy/rpc/_registry.py`) — the allowlist pattern: qualified-name tags, closed `BUILTIN_META_TAGS` set, no client-controlled class resolution.

This change wires that stack into the realtime composables as an additive typed layer over the text transport from `feat-websocket-composable`.

## Goals / Non-Goals

**Goals:**

- `use_websocket(url, *, message_type=T, strict=True, ...)` — typed iterator `AsyncIterator[T]` + typed `.send(T)`, reusing every other behavior of the raw handle (sharing, reconnect, `.state`, `.last_close`, close/lifecycle semantics).
- Wire envelope: single JSON object per frame = encoded payload + `__webcompy_transfer_meta__` member (typed-response body wire mode).
- Skip-on-error receive semantics with `.last_error: Signal[Exception | None]` + warning; subscription survives bad frames.
- App-scoped type allowlist via `register_realtime_type_handler`, no module-level globals.
- Dataclass-only targets, clear error otherwise.

**Non-Goals:**

- Typed SSE, non-dataclass targets, schema negotiation, replay, hydration transfer (see proposal Non-goals).

## Decisions

### D1: Typed layer wraps the raw handle; transport/sharing/reconnect are untouched

The typed handle composes over the raw WebSocket handle: it owns the pump-side deserialization and the send-side encoding, delegating connection management entirely to `feat-websocket-composable`. Rationale: sharing/reconnect policy is transport concern; typing is a codec concern. Keeping them separate means the typed layer is small and the raw composable's spec is not modified (the `message_type` parameter is specified in this capability as additive prose-linked behavior). Alternative considered (modifying `websocket-composable` requirements) rejected: that capability belongs to the predecessor change and this layering keeps both independently validatable.

### D2: Body wire mode envelope; dataclass-only targets

Frames are `{**encode_with_meta(instance), "__webcompy_transfer_meta__": meta}`. Because `merge_meta_into_body` requires a top-level object, `message_type` SHALL be a dataclass; other targets raise immediately. Rationale: reuses the exact wire format already specified in `typed-response`, so peers that speak typed-response can interoperate, and `feat-rpc-websocket` reuses the envelope unchanged. Alternative considered (envelope wrapper `{"data": ..., "meta": ...}` to support lists/scalars) rejected: it forges a second wire format for marginal use cases.

### D3: Skip-on-error with `.last_error`, never kill the stream

A frame that fails JSON parsing, meta validation, or `from_json` reconstruction is skipped: not yielded, `.last_error` set, warning logged. The subscription and the shared connection survive. Rationale: realtime streams are long-lived; one malformed message (schema drift, partial deploy) must not tear down every consumer of a shared connection. This mirrors the AsyncResult-style out-of-band error surface adopted by `signal-stream`. Alternative considered (raise into the iterator) rejected: it would kill the consumer's pump loop for a transient data problem.

### D4: `strict=True` by default for typed frames

Receive-side reconstruction uses `strict=True` (reject unknown/extra fields) by default, with `strict=False` opt-in. Rationale: realtime peers are usually deployed together; strictness catches schema drift loudly at the boundary, consistent with json-rpc's strict server-side decoding. The skip-on-error path (D3) makes strictness survivable.

### D5: App-scoped allowlist registry mirroring the json-rpc pattern

`register_realtime_type_handler(cls, encoder, decoder)` registers qualified-name-tag handlers in an app-DI-scope registry (same inject-or-provide pattern as the connection registry). Send-side passes these as `type_handlers` to `encode_with_meta`; receive-side passes matching decoders to `apply_transfer_meta`/`from_json`. Builtin tags (`datetime`, `UUID`, `Decimal`, …) always work; unregistered tags are rejected (skip-on-error), never resolved by name. Rationale: reuses the security posture from `json-rpc` (no client-controlled class resolution) and respects No-New-Globals. Alternative considered (module-level registry) rejected: invariant violation and cross-app leakage.

### D6: SSR/hydration unchanged

Typed handles during SSR behave exactly like the raw handle (empty iterator, `CLOSED`, warning); typed messages and `.last_error` are never transferred. Rationale: connections and streams are client-runtime concerns (consistent with the predecessor changes).

## Risks / Trade-offs

- [A poison frame skips silently in the UI if `.last_error` is unobserved] → Warning is always logged; docs recipe shows rendering an error badge from `.last_error`.
- [Strict default rejects forward-compatible additive fields from a newer server] → `strict=False` opt-in documented; strict default chosen deliberately for drift detection.
- [Allowlist is app-scoped, so registrations must be repeated per app] → Consistent with DI-scoped registries; documented in the registration API docs.
- [Envelope requires object payloads, excluding list/scalar messages] → Accepted (D2); users wrap collections in a dataclass.

## Open Questions

(none)
