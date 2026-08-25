## 1. HttpClient fidelity fixes

- [ ] 1.1 Remove `urllib.parse.quote` wrapping on request headers in `packages/webcompy/src/webcompy/ajax/_fetch.py:228` — replace `req_headers = {quote(str(k)): quote(str(v)) ...}` with a plain copy of `raw_headers` so caller-supplied `Content-Type` with `;`/`=` is not percent-encoded
- [ ] 1.2 Preserve `body_data` type in `packages/webcompy/src/webcompy/ajax/_fetch.py:284` — change `body = body_data if isinstance(body_data, str) else body_data.decode()` to `body = body_data`
- [ ] 1.3 Remove unused `urllib.parse` import if no longer needed elsewhere in the file, otherwise keep it for `query_params` `urlencode`

## 2. Tests

- [ ] 2.1 Extend `tests/test_ajax.py` with raw-body fidelity tests using `FakeFetchPort`: (a) `body_data=b"\x00\x01\xff"` round-trips as `bytes`, (b) non-UTF-8 bytes `b"\xff\xfe"` does not raise, (c) `body_data="hello"` round-trips as `str`
- [ ] 2.2 Add header-fidelity tests in `tests/test_ajax.py`: (a) explicit `Content-Type: multipart/form-data; boundary=custom` with `form_data` is not mangled, (b) explicit `Content-Type: application/json; charset=utf-8` with `json` is preserved
- [ ] 2.3 Verify existing `FakeFetchPort` bytes-caching tests in `tests/test_fetch_port_bytes_body.py` still pass (deterministic SHA-256 keys)

## 3. Validation

- [ ] 3.1 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`
- [ ] 3.2 Run `uv run python -m pytest tests/test_ajax.py tests/test_fetch_port_bytes_body.py -q`
- [ ] 3.3 Run `openspec validate fix-preserve-bytes-body --strict` and resolve any issues
