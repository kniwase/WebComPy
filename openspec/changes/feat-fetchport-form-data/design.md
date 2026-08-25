## Context

`HttpClient.request()` currently has two dispatch paths: `json` / `body_data` go through `inject(FETCH_PORT_KEY).fetch(...)` with `body: str | None`, while `form_data` / `form_element` bypass the port entirely — importing `_raw_browser` inside the function and using `FFI_PORT_KEY` to proxy headers (see proposal.md for why this is a problem). The `FetchPort` implementations are `BrowserFetchPort` (PyScript `fetch`, where Pyodide converts Python `bytes` to JS `Uint8Array`), `ServerFetchPort` (httpx with `content=`, which already accepts `bytes`), and `FakeFetchPort` (records nothing about body). No existing unit or E2E tests exercise the `form_data` path.

## Goals / Non-Goals

**Goals:**

- One request path in `HttpClient`: everything goes through the injected `FetchPort`.
- Multipart encoding that works identically across browser, server, and testing ports.
- Deterministic, spec-compliant wire format (`multipart/form-data` per RFC 7578).

**Non-Goals:**

- Changing `form_element` semantics beyond a better non-browser error message.
- Streaming/chunked multipart upload.
- Exposing multipart helpers as public API.

## Decisions

### D1. Encode multipart at the client layer; extend port body to `str | bytes`

`HttpClient` encodes `form_data` into bytes via a new private encoder and sends it as an ordinary `body`. The ABC signature widens from `body: str | None` to `body: str | bytes | None`.

- *Alternatives considered*:
  - Keep `str`-only port and encode to text — rejected: binary field values would require lossy decoding or base64 inflation.
  - Add a `form=` parameter to `FetchPort.fetch()` so each implementation encodes natively (browser → JS `FormData`, server → httpx `files=`) — rejected: triples the encoding logic, makes cross-port behavior diverge, and complicates fake-based testing.
  - Use httpx's internal multipart encoder on the server only — rejected: not shared code and relies on a private module.

### D2. Hand-rolled stdlib encoder with alphanumeric boundary

New module `webcompy/ajax/_multipart.py`: `encode_multipart(fields: dict[str, str | bytes]) -> tuple[bytes, str]` returning `(body_bytes, content_type_value)`. Boundary is generated with `secrets.token_hex(16)`.

Rationale for alphanumeric-only boundaries: `HttpClient.request()` applies `urllib.parse.quote` to every header value it builds. A default-safe quote leaves `/` intact but percent-encodes `;`, `-` is safe, yet relying on `quote`'s safe-set is fragile; hex digits sidestep the issue entirely. Field names/values are UTF-8 encoded; `bytes` values pass through verbatim.

- *Alternative*: use `uuid.uuid4().hex` — equivalent; `secrets` chosen to signal unpredictability intent.

### D3. Content-Type handling

When `form_data` is provided and the caller did not explicitly set a `Content-Type` header, the client sets `Content-Type: multipart/form-data; boundary=<boundary>`. An explicit caller-supplied `Content-Type` wins and is left untouched (callers who need exotic subtypes can opt out of auto-boundary behavior at their own risk).

### D4. Cache keys hash bytes bodies

`BrowserFetchPort._cache_key` / `ServerFetchPort._cache_key` currently interpolate `body` into an f-string. With bytes bodies this yields unstable reprs. Both normalize non-str bodies via SHA-256 hex digest (`hashlib.sha256(body).hexdigest()`) before interpolation, keeping keys deterministic and bounded.

### D5. `form_element` stays browser-only

The DOM-dependent path cannot be made transport-portable (no DOM during SSR). It keeps its dedicated branch but now raises `WebComPyHttpClientException` with a message explaining that `form_element` requires a browser environment when `_raw_browser is None`, instead of a bare exception.

## Risks / Trade-offs

- [Hand-rolled encoder deviates from browser `FormData` edge cases, e.g. filename parts] → Out of scope by design: `form_data` values are `str | bytes` name/value pairs only; the encoder targets exactly RFC 7578's simple-field subset, covered by unit tests against a golden format.
- [Widening the ABC breaks external `FetchPort` implementations that override `fetch`/`stream` with `body: str | None`] → First-party implementations updated in the same change; the widening is contravariant-compatible for callers. Documented as **BREAKING** in the proposal.
- [Multipart bodies bypass the hydration response cache keying assumptions] → Cache keys remain `(method, url, hashed-body)`; POST responses were never transferred via hydration transfer (self-site GET focus), unchanged.
- [Boundary collision with payload content] → Probability negligible with 128-bit random hex; no mitigation needed beyond standard practice.

## Migration Plan

No data migration. Rollback is a plain revert: the public `HttpClient` API (parameter names and types) does not change; only internals and the port body type do.

## Open Questions

None.
