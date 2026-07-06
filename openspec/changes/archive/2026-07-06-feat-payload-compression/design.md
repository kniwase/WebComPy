# Design: Payload Compression

## Context

The hydration data transfer payload is embedded as a `<script type="application/json" id="__webcompy_data__">` tag in the HTML output. After `feat-signal-value-transfer`, the payload includes Signal values, which can significantly increase its size for stateful applications. The payload is transferred as part of the initial HTML response, so larger payloads increase page weight and parse time.

Both server (CPython) and browser (PyScript/Emscripten) need to handle the payload. The compression algorithm must be available in both environments.

## Goals / Non-Goals

**Goals:**

- Compress the serialized payload using gzip (stdlib `zlib`) when it exceeds a configurable threshold.
- Base64-encode the compressed bytes so they can be embedded in a JSON/HTML context safely.
- Make compression transparent: the deserializer auto-detects compressed payloads.
- Use only stdlib modules (`zlib`, `base64`) — no external dependencies.

**Non-Goals:**

- Brotli compression (requires native extension, may not work under PyScript).
- Per-section or incremental compression.
- HTTP-level response compression (handled by web server middleware).
- Runtime-selectable compression algorithms.

## Decisions

### D1: Gzip via stdlib `zlib`

The payload SHALL be compressed using `zlib.compress(data)` and decompressed using `zlib.decompress(data)`. The `zlib` module is part of the Python standard library and is compiled into CPython. Under PyScript/Emscripten, `zlib` is available because Emscripten provides zlib support and Pyodide includes it.

**Alternatives considered:**
- **Brotli**: Better compression ratio than gzip, but requires the `brotli` or `brotlic` third-party package (native extension). May not work under PyScript/Emscripten. Deferred.
- **LZMA (`lzma` module)**: Higher compression ratio than gzip but slower. Available in stdlib but may have Emscripten support issues. Overkill for typical payload sizes.
- **No compression**: Rejected — payload size growth from Signal transfer justifies the feature.

### D2: Compression envelope structure

When compressed, the payload JSON is replaced with an envelope:

```json
{
    "__webcompy_compressed__": true,
    "__webcompy_transfer_version__": 2,
    "data": "<base64-encoded gzip-compressed original JSON>"
}
```

The `__webcompy_compressed__` flag signals the deserializer to:
1. Base64-decode the `data` field.
2. Gzip-decompress the result.
3. JSON-parse the decompressed string.

**Rationale:** The envelope approach keeps the version field accessible without decompression (for diagnostics) and uses the reserved `__webcompy_` prefix consistent with the codec's type-tag convention.

### D3: Threshold-based activation

Compression SHALL only be applied when the serialized JSON exceeds a configurable byte threshold (`compression_threshold`). The default threshold SHALL be 1024 bytes. Payloads below the threshold SHALL be stored uncompressed (avoiding the base64 overhead, which increases size by ~33% for small payloads).

**Threshold tuning:**
- For small payloads (< threshold), compression + base64 expansion can actually increase size.
- The threshold should be set above the breakeven point where gzip compression savings exceed base64 expansion overhead.
- 1024 bytes is a conservative default. The threshold SHALL be configurable via `WebComPyAppConfig` or `GenerateConfig`.

### D4: `__webcompy_compressed__` flag is independent of version

The compression flag is orthogonal to `__webcompy_transfer_version__`. A version 2 payload can be compressed or uncompressed. The deserializer checks the flag first, decompresses if needed, then proceeds with version-based parsing. This avoids coupling two independent concerns.

### D5: Compression level

`zlib.compress(data, level)` accepts a level (0-9). The default SHALL be `zlib.Z_DEFAULT_COMPRESSION` (level 6), which balances speed and ratio. The level SHALL not be configurable in this change (deferred to future tuning).

## Risks / Trade-offs

- **[zlib under PyScript]** → Mitigation: Validation spike. Use `webcompy inspect` CLI to verify `zlib.compress()` / `zlib.decompress()` work under PyScript/Emscripten. Pyodide documentation indicates zlib is supported.

- **[Base64 expansion offsetting compression gains for small payloads]** → Mitigation: The threshold parameter prevents compressing small payloads. Default threshold (1024 bytes) ensures compression is only applied when net savings are expected.

- **[Compression CPU cost]** → Mitigation: `zlib` level 6 is fast for typical payload sizes (tens of KB). For very large payloads (MBs), compression may add latency, but this is an inherent trade-off for reduced transfer size.

- **[Backward compatibility]** → Mitigation: Uncompressed payloads (no `__webcompy_compressed__` flag) decode exactly as before. The feature is purely additive.

## Open Questions

1. **Should the threshold be per-app or per-payload?** The threshold is set at the app/config level (`WebComPyAppConfig` or `GenerateConfig`). Each payload is independently evaluated against the threshold. Decision: per-app config, evaluated per-payload.

2. **Should compression be disableable?** Setting `compression_threshold=None` or `0` disables compression entirely. This is the escape hatch for environments where compression is undesirable.
