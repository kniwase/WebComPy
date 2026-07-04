# Proposal: Payload Compression

## Why

After `feat-signal-value-transfer`, the hydration data transfer payload includes Signal values alongside `AsyncResult` data and `FetchPort` response caches. For applications with significant server-side state, the payload (embedded as a `<script type="application/json" id="__webcompy_data__">` tag in the HTML) can grow substantially, increasing page size and parse time.

This change adds optional gzip compression to the transfer payload. When the serialized payload exceeds a configurable threshold, it SHALL be gzip-compressed (using stdlib `zlib`/`gzip`), base64-encoded, and marked with a `compressed: true` flag in the payload metadata. The browser-side deserializer detects the flag and decompresses accordingly.

## What Changes

- **MODIFIED** `packages/webcompy/src/webcompy/hydration/_payload.py`:
  - `serialize_payload()` SHALL accept a `compression_threshold: int | None` parameter (default e.g., 1024 bytes). When the serialized JSON exceeds the threshold, the payload SHALL be gzip-compressed via `zlib.compress()`, base64-encoded, and wrapped in a `{"__webcompy_compressed__": true, "data": "<base64>"}` envelope.
  - `deserialize_payload()` SHALL detect the `__webcompy_compressed__` flag, base64-decode and gzip-decompress the `data` field before JSON parsing.
  - The `__webcompy_transfer_version__` SHALL remain at the current version (compression is an orthogonal concern, signaled by the `__webcompy_compressed__` flag rather than a version bump).
- **MODIFIED** SSR/SSG entry points that call `serialize_payload()` — Pass the `compression_threshold` from `WebComPyAppConfig` or `GenerateConfig`.

## Capabilities

### New Capabilities

- `payload-compression`: Optional gzip compression of the hydration data transfer payload. Activated when the serialized payload exceeds a configurable byte threshold. Uses stdlib `zlib` for compression (pure Python, works in both CPython and PyScript/Emscripten). The compressed payload is base64-encoded and marked with a `__webcompy_compressed__` flag for browser-side detection.

### Modified Capabilities

- `hydration-data-transfer`: `serialize_payload()` and `deserialize_payload()` SHALL support compressed payloads. The compression flag is signaled via `__webcompy_compressed__` in the payload envelope, independent of `__webcompy_transfer_version__`.

## Known Issues Addressed

- **Payload size growth from Signal value transfer** — `feat-signal-value-transfer` adds the `signals` section, increasing payload size for stateful applications. Compression mitigates this.

## Non-goals

- **Brotli compression** — Brotli typically requires a native extension (`brotli` or `brotlic` package) that may not work under PyScript/Emscripten. Gzip via stdlib `zlib` is universally available. Brotli can be added as an optional layer in a future change.
- **Per-section compression** — The entire payload is compressed as a single blob. Individual sections (`fetches`, `async_results`, `signals`) are not compressed independently.
- **HTTP-level compression (Content-Encoding: gzip)** — This change compresses the payload embedded in the HTML, not the HTTP response. HTTP-level compression is handled by the web server (Starlette/uvicorn GZip middleware) and is orthogonal.
- **Changing the compression algorithm at runtime** — The algorithm is fixed (gzip/zlib). A registry for multiple algorithms is deferred.
- **Changing the public API of `serialize_payload()` beyond the optional threshold parameter** — The compression is transparent to callers who use the default threshold.

## Dependencies

- **Benefits from** `feat-signal-value-transfer` — Compression is most valuable when the payload includes Signal values. However, compression can be applied to any payload version (v1 or v2), so it is not a hard dependency.

## Impact

- **Affected modules**:
  - `packages/webcompy/src/webcompy/hydration/_payload.py` (compression/decompression logic)
- **Breaking**: None. Compression is opt-in via the threshold parameter. Existing payloads without compression decode correctly (the `__webcompy_compressed__` flag is absent, signaling uncompressed).
- **Backward compatible**: An uncompressed payload (no `__webcompy_compressed__` flag) is decoded exactly as before.
- **Testing**: Unit tests for compression round-trip, threshold boundary, and backward compatibility with uncompressed payloads. Verification that `zlib` works under PyScript (validation spike).
