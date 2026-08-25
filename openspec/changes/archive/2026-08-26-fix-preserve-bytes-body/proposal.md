## Why

`#280` widened `FetchPort.fetch()/stream()` to `body: str | bytes | None` and made all first-party ports pass bodies unchanged, but `HttpClient.request` still has two leftover fidelity bugs from the pre-bytes era: (1) `body_data: bytes` is forced through `bytes.decode()` before reaching the port, so non-UTF-8 binary payloads fail or corrupt; (2) every request header value is wrapped in `urllib.parse.quote`, so a caller-supplied `Content-Type` containing `;`/`=` (e.g. `multipart/form-data; boundary=...` or `application/json; charset=utf-8`) is percent-encoded and arrives at the transport mangled. Both are latent bugs surfaced by the `#280` review (`Should Improve` + `Note`) and should be fixed together as a small polish follow-up while `HttpClient` is still being touched.

## What Changes

- Preserve `body_data` fidelity: change `packages/webcompy/src/webcompy/ajax/_fetch.py:284` from `body = body_data if isinstance(body_data, str) else body_data.decode()` to `body = body_data` so `str` stays `str` and `bytes` stays `bytes` through the injected `FetchPort`.
- Preserve header fidelity: remove the `urllib.parse.quote` wrapping on request header names/values in `HttpClient.request` (`_fetch.py:228`) so caller-supplied headers — especially `Content-Type` with `; boundary=` or `; charset=` — are passed unchanged to the port. Auto-generated `Content-Type` values (`application/json`, multipart `boundary=...`) remain unquoted as before.
- Add delta spec and unit tests covering: binary `body_data` round-trips through `FakeFetchPort`, non-UTF-8 bytes not raising, `str` pass-through unchanged, and `Content-Type` with `;` preserved.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `typed-api-client`: `HttpClient` SHALL preserve raw-body and header fidelity when routing through `FetchPort` — `body_data` keeps its original `str`/`bytes` type, and header values are not percent-encoded.

## Impact

- Code: `packages/webcompy/src/webcompy/ajax/_fetch.py` (two small edits, no new modules).
- Behavior: binary `body_data` no longer decodes/corrupts; explicit `Content-Type` with `;` now works. Existing `str` bodies and `;`-free `Content-Type` values are unaffected.
- Dependencies: none.
- Tests: `tests/test_ajax.py` extended with raw-body and header-fidelity cases.

## Known Issues Addressed

None of the tracked known issues are addressed; this change fixes polish items from the `#280` review.

## Non-goals

- Changing `FetchPort` ABC or any port implementation (already bytes-capable after `#280`).
- Excluding non-idempotent POSTs from SSR hydration transfer (the third review `Note` — deferred as not yet material).
- Streaming or chunked body upload.
