# Proposal: Transfer Codec Engine

## Why

WebComPy's hydration data transfer (`feat-suspense-and-hydration-data-transfer`) serializes server-resolved `AsyncResult` data and `FetchPort` response caches into a JSON payload embedded in the HTML. The current serialization (`hydration/_payload.py`) uses `json.dumps(value)` with a `default=str` fallback — any non-JSON-serializable value (datetime, set, enum, dataclass, Decimal, bytes, tuple) is silently dropped or stringified, losing type information and breaking hydration fidelity.

The upcoming `feat-signal-value-transfer` change will extend transfer to all Signal values, where the variety of stored types is far broader than AsyncResult data. A robust, extensible serialization engine is needed before Signal transfer can be reliable. This change introduces a layered codec inspired by superjson: a pure-Python extended encoder/decoder covering common standard-library types, with a pluggable type-handler registry for custom and third-party types.

## What Changes

- **NEW** `packages/webcompy/src/webcompy/hydration/_codec.py` — The extended codec engine:
  - `encode(value: Any) -> Any` — Recursively encodes a Python value into a JSON-safe structure. Non-serializable types are wrapped in type-tagged dicts using a reserved `__webcompy_type__` / `__webcompy_value__` key pair.
  - `decode(value: Any) -> Any` — Recursively decodes a JSON-parsed structure back into Python objects, reconstructing typed values from type-tagged dicts.
  - `register_type_handler(cls: type, encoder: Callable[[Any], dict], decoder: Callable[[dict], Any]) -> None` — Layer 2 plugin API for custom and third-party type support.
  - Built-in Layer 1 type handlers for: `datetime.datetime`, `datetime.date`, `datetime.time`, `set`, `frozenset`, `enum.Enum`, `bytes`, `decimal.Decimal`, `dataclasses.dataclass` instances, `tuple`, `pathlib.Path`, `uuid.UUID`.
- **MODIFIED** `packages/webcompy/src/webcompy/hydration/_payload.py` — `_try_serialize_value()` and `serialize_payload()` use `encode()` instead of `json.dumps()` probing. `deserialize_payload()` uses `decode()` after JSON parsing. `TransferPayload.__webcompy_transfer_version__` bumps to `2` when the `signals` section is present (introduced by `feat-signal-value-transfer`); the codec itself is version-agnostic and works with both v1 and v2 payloads.
- **MODIFIED** `packages/webcompy/src/webcompy/hydration/_collect.py` — Uses `encode()` when serializing `AsyncResult` data for the payload (instead of raw `entry.data`).

## Capabilities

### New Capabilities

- `transfer-codec`: A layered serialization engine for hydration data transfer. Layer 0 wraps stdlib JSON for basic types. Layer 1 provides pure-Python encoders/decoders for common standard-library types (datetime, set, enum, dataclass, etc.). Layer 2 exposes a plugin API for custom type handlers. All type tags use a reserved `__webcompy_` key prefix to avoid collisions with user data.

### Modified Capabilities

- `hydration-data-transfer`: `TransferAsyncResultEntry.data` and `TransferFetchEntry.body` SHALL be encoded/decoded via the codec engine instead of raw `json.dumps`. Non-serializable values are no longer silently dropped (unless they fail even the extended codec, in which case they are dropped with a warning as before).

## Known Issues Addressed

- **Non-serializable AsyncResult data silently dropped** — Currently, if `AsyncResult` data contains a `datetime` or `dataclass`, it is either stringified (`default=str`) or dropped entirely. The codec engine preserves type information so the browser reconstructs the correct type.

## Non-goals

- **Signal value transfer** — This change provides the codec engine only. Collecting and restoring Signal values is `feat-signal-value-transfer`.
- **Payload compression** — gzip/brotli compression is `feat-payload-compression`. The codec produces uncompressed JSON; compression is applied at a higher layer.
- **Pydantic as a core dependency** — Pydantic v2's `pydantic-core` is Rust-backed and may not work in PyScript/Emscripten. Pydantic integration is deferred to a separate optional plugin that registers handlers via `register_type_handler()`. The codec's Layer 2 API is designed to accommodate it.
- **Custom transfer keys** — Type tags use the reserved `__webcompy_` prefix. User-defined keys are not supported (the prefix is framework-reserved).
- **Circular reference reconstruction** — Circular references in transferred values are detected and dropped with a warning (not reconstructed).
- **Changing the `TransferPayload` schema version** — The codec is version-agnostic. The payload version bump to 2 happens in `feat-signal-value-transfer` (which adds the `signals` section).

## Impact

- **Affected modules**:
  - `packages/webcompy/src/webcompy/hydration/_codec.py` (new)
  - `packages/webcompy/src/webcompy/hydration/_payload.py` (modified — encode/decode integration)
  - `packages/webcompy/src/webcompy/hydration/_collect.py` (modified — encode AsyncResult data)
  - `packages/webcompy/src/webcompy/hydration/__init__.py` (export public codec API)
- **Breaking**: None. The codec is backward-compatible with existing v1 payloads (type-tagged dicts only appear where the encoder wraps non-JSON values; plain JSON values are unchanged).
- **Backward compatible**: Existing AsyncResult data that is plain JSON-serializable encodes identically to before. The codec only adds type tags for values that `json.dumps` would fail on or stringify.
- **Testing**: Unit tests for each Layer 1 type handler (encode + decode round-trip), circular reference detection, plugin API registration, and backward compatibility with plain JSON values.
