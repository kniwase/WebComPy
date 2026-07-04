## 1. Compression Logic

- [ ] 1.1 Add `compression_threshold: int | None = 1024` parameter to `serialize_payload()` in `packages/webcompy/src/webcompy/hydration/_payload.py`
- [ ] 1.2 After JSON serialization and HTML escaping, check if the byte length exceeds `compression_threshold`
- [ ] 1.3 If threshold is exceeded (and threshold is not `None` or `0`), compress the JSON string via `zlib.compress(json_str.encode("utf-8"))`
- [ ] 1.4 Base64-encode the compressed bytes via `base64.b64encode(compressed).decode("ascii")`
- [ ] 1.5 Wrap in envelope: `{"__webcompy_compressed__": true, "__webcompy_transfer_version__": <version>, "data": "<base64>"}`
- [ ] 1.6 HTML-escape the envelope JSON string and return

## 2. Decompression Logic

- [ ] 2.1 In `deserialize_payload()`, after `html_module.unescape()` and `json.loads()`, check for `"__webcompy_compressed__"` key
- [ ] 2.2 If present and `true`, extract the `"data"` field, base64-decode via `base64.b64decode(data)`
- [ ] 2.3 Gzip-decompress via `zlib.decompress(decoded_bytes)`
- [ ] 2.4 Decode to string via `.decode("utf-8")`, then `json.loads()` the decompressed string
- [ ] 2.5 Proceed with normal version-based `TransferPayload` construction
- [ ] 2.6 If `"__webcompy_compressed__"` is absent, process as uncompressed (existing path)

## 3. Imports

- [ ] 3.1 Add `import zlib` and `import base64` to `packages/webcompy/src/webcompy/hydration/_payload.py`

## 4. Validation Spike

- [ ] 4.1 Verify `zlib.compress()` and `zlib.decompress()` work under PyScript using `webcompy inspect` CLI with a minimal test — confirm gzip compression/decompression round-trips in the browser environment

## 5. Unit Tests

- [ ] 5.1 Test compression round-trip: serialize with threshold → deserialize → original payload preserved
- [ ] 5.2 Test payload below threshold is not compressed (no `__webcompy_compressed__` key)
- [ ] 5.3 Test `compression_threshold=None` disables compression
- [ ] 5.4 Test `compression_threshold=0` disables compression
- [ ] 5.5 Test backward compatibility: uncompressed payload (no flag) deserializes correctly
- [ ] 5.6 Test compressed payload is smaller than uncompressed for typical Signal-heavy data
- [ ] 5.7 Test envelope contains `__webcompy_transfer_version__` at top level

## 6. Verification

- [ ] 6.1 Run `uv run ruff check .` and `uv run ruff format --check .`
- [ ] 6.2 Run `uv run pyright`
- [ ] 6.3 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 6.4 Run `scripts/run-e2e-tests.sh` — verify hydration data transfer works with compression enabled
- [ ] 6.5 `npx @fission-ai/openspec@latest validate` passes
