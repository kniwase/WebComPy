## 1. Multipart encoder

- [x] 1.1 Create `packages/webcompy/src/webcompy/ajax/_multipart.py` with `encode_multipart(fields: dict[str, str | bytes]) -> tuple[bytes, str]` (stdlib only, `secrets.token_hex(16)` boundary, UTF-8 encoding for str values, docstrings on the public function)
- [x] 1.2 Add unit tests covering: field ordering, str and bytes values, CRLF framing, boundary uniqueness, and the returned `Content-Type` media type

## 2. FetchPort body type extension

- [ ] 2.1 Widen `body` to `str | bytes | None` in `FetchPort.fetch()` and `FetchPort.stream()` in `packages/webcompy/src/webcompy/ports/_fetch.py`, including docstring updates
- [ ] 2.2 Update `BrowserFetchPort.fetch()` / `.stream()` annotations and normalize `_cache_key` to hash non-str bodies via SHA-256
- [ ] 2.3 Update `ServerFetchPort.fetch()` and `FakeFetchPort.fetch()` / `.stream()` annotations with docstring updates
- [ ] 2.4 Add unit tests: binary body passes through a fake port unchanged; deterministic cache-key behavior for repeated identical bytes bodies

## 3. HttpClient integration

- [ ] 3.1 Rewrite the form branch in `HttpClient.request()` (`packages/webcompy/src/webcompy/ajax/_fetch.py`) so `form_data` is multipart-encoded and dispatched through `inject(FETCH_PORT_KEY).fetch(...)`; set `Content-Type` only when the caller did not supply one
- [ ] 3.2 Remove the direct `_raw_browser` import and `FFI_PORT_KEY` usage from the `form_data` path; keep a slim browser-only branch for `form_element` that raises `WebComPyHttpClientException` with a descriptive message outside the browser
- [ ] 3.3 Add unit tests using `FakeFetchPort`: SSR-style self-site POST with `form_data`, explicit caller `Content-Type` preserved, and non-browser `form_element` error message
- [ ] 3.4 Verify no remaining references to `_raw_browser` / `FFI_PORT_KEY` in `webcompy/ajax/`

## 4. Specs, docs, and validation

- [ ] 4.1 Run `scripts/check-docstrings.py` and fix any coverage or style gaps introduced by this change
- [ ] 4.2 Run local CI checks: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short`
- [ ] 4.3 Run `openspec validate feat-fetchport-form-data --strict` and resolve any issues
