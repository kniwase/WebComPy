## Why

`HttpClient`'s `form_data` path is the only request route that bypasses the injectable `FetchPort`: it imports the raw browser object directly and manages an FFI proxy itself, so form submissions cannot run during SSR/SSG, cannot be faked in unit tests, and violate the port-abstraction principle that browser runtime code must not touch the monolithic `browser` object.

## What Changes

- Add a stdlib-only multipart/form-data encoder (`webcompy/ajax/_multipart.py`) that converts `dict[str, str | bytes]` fields into an RFC 7578 byte body plus a `Content-Type` header value with an alphanumeric-only boundary.
- Extend the `FetchPort` ABC so `fetch()` and `stream()` accept `body: str | bytes | None` (previously `str | None`). **BREAKING** for third-party `FetchPort` implementations that pin `body: str | None`; all first-party implementations remain source-compatible.
- Route `HttpClient.request(form_data=...)` through the encoded multipart body over the injected `FetchPort`, removing the direct `_raw_browser` import and `FFI_PORT_KEY` proxy usage from `webcompy/ajax/_fetch.py`.
- Keep `form_element` as a browser-only escape hatch; improve its non-browser failure to raise a descriptive error message.
- Normalize `BrowserFetchPort._cache_key` so bytes bodies produce deterministic cache keys.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `port-abstraction`: The `FetchPort.fetch()` / `stream()` body parameter SHALL accept `str | bytes | None`, passed to the underlying transport unchanged; implementations SHALL NOT assume a text body.
- `typed-api-client`: `HttpClient` form requests (`form_data`) SHALL be routed through the injected `FetchPort` as multipart-encoded bodies instead of bypassing it with direct browser access.

## Impact

- Code: `packages/webcompy/src/webcompy/ajax/` (new `_multipart.py`, `_fetch.py` rewrite of the form branch), `packages/webcompy/src/webcompy/ports/_fetch.py` (ABC), `packages/webcompy/src/webcompy/ports/_browser/_fetch.py`, `packages/webcompy-server/src/webcompy_server/ports/_fetch.py`, `packages/webcompy-testing/src/webcompy_testing/_ports.py`.
- Behavior: form submissions now work during SSR/SSG via self-site ASGI fetch and become testable with `FakeFetchPort`. Browser behavior for `form_data` is preserved (multipart encoding replaces JS `FormData`; wire format remains standard `multipart/form-data`).
- Dependencies: none added (stdlib only).
- Tests: new unit tests for the encoder and the FetchPort-routed form path.

## Known Issues Addressed

None of the listed known issues are directly addressed; this change removes an architectural deviation from the port abstraction rather than a tracked known issue.

## Non-goals

- Deprecating or removing `form_element` (it stays as a browser-only escape hatch).
- Streaming multipart upload for large file payloads.
- Adding a `form=` parameter to the `FetchPort` interface (rejected alternative).
