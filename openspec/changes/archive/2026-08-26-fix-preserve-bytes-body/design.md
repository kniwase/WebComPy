## Context

See `proposal.md` for why. Current state after `#280` (`feat/fetchport-form-data`):

- `FetchPort.fetch()/stream()` already accept `body: str | bytes | None` and first-party ports (`BrowserFetchPort`, `ServerFetchPort`, `FakeFetchPort`) pass the body unchanged to their transports (`browser.fetch` / `httpx content=`). Cache keys for bytes bodies are hashed via SHA-256.
- `HttpClient.request` in `packages/webcompy/src/webcompy/ajax/_fetch.py` still has two pre-bytes leftovers: `body_data: bytes` is forced through `bytes.decode()` at `_:284`, and every header key/value is wrapped in `urllib.parse.quote` at `_:228`. The former breaks non-UTF-8 binaries; the latter mangles `Content-Type` with `;`/`=`. Auto-generated multipart `Content-Type` was worked around in `#280` by using an alnum hex boundary and setting the header unquoted *after* quoting, but an explicit caller-supplied `Content-Type` containing `; boundary=` is still quoted.

No new modules or port changes are needed — only two small edits in `HttpClient.request`.

## Goals / Non-Goals

**Goals:**

- Make `HttpClient.request` pass `body_data` and headers with full fidelity to the bytes-capable `FetchPort`, matching the `port-abstraction` invariant that ports receive the body unchanged.
- Keep the change minimal and reviewable (two lines in one file plus tests).

**Non-Goals:**

- Changing `FetchPort` ABC or any port implementation.
- Filtering POSTs out of `ServerFetchPort.get_transfer_data()` (third review `Note` — deferred until payload bloat is observed).
- Any wire-format or public-API change (`HttpClient` signature stays `body_data: str | bytes | None`).

## Decisions

### D1. Preserve `body_data` type: `body = body_data`

Change `_fetch.py:284` from `body = body_data if isinstance(body_data, str) else body_data.decode()` to `body = body_data`.

- *Why*: `FetchPort` already handles both `str` and `bytes` (httpx `content=` accepts both; browser `fetch` via Pyodide maps `bytes` to `Uint8Array`). No decoding is needed and it loses fidelity.
- *Alternatives considered*:
  - Keep `decode()` with `errors="surrogateescape"` — rejected: still corrupts true binaries and hides the bug.
  - Normalize all bodies to `bytes` (`str.encode("utf-8")`) — rejected: would change `str` callers' wire bytes and diverge from existing `json_dumps(...)` returning `str`; ports accept both, so preservation is simpler.

### D2. Stop percent-encoding header values

Replace `_fetch.py:228` `req_headers = {quote(str(k)): quote(str(v)) for k,v in raw_headers.items()}` with `req_headers = dict(raw_headers)` (copy, no quoting). Remove the now-unused `urllib.parse` import if it becomes unused elsewhere, otherwise keep it for `urlencode` of `query_params`.

- *Why*: HTTP header values are not URL components; `quote` is only correct for `query_params` (already handled by `urlencode`). Quoting mangles `;`, `=`, `,` in `Content-Type` and any other structured header. `form_data` auto-generated `Content-Type` already bypassed quoting by setting the header after quoting; removing quoting makes explicit caller values work the same way.
- *Alternatives considered*:
  - `quote(v, safe="; =/")` — rejected: allowlist is fragile and still encodes `,` etc.
  - Quote only keys or exclude `Content-Type` — rejected: partial fix, other headers would still mangle.
  - Keep quoting but document exotic types as "at your own risk" — rejected: latent bug with trivial fix, and the review explicitly suggests fixing if common.
- *Risk*: If some caller relied on quoting (e.g. passing non-ASCII header values expecting percent-encoding), behavior would change. Header values with non-ASCII are already out-of-spec per RFC 7230 and not used in this codebase; no existing test depends on quoting.

## Risks / Trade-offs

- [Removing `quote` changes behavior for exotic headers] → No caller in repo passes non-ASCII header values expecting quoting; existing test `test_explicit_content_type_wins` uses `application/x-custom` without `;` and will still pass. New tests with `;` will lock the correct behavior.
- [Binary `body_data` now reaches `httpx`/`browser.fetch` as bytes] → Both transports already accept `bytes`; `ServerFetchPort` and `BrowserFetchPort` cache keys already hash bytes via SHA-256, so caching remains deterministic.
- [No spec change to `port-abstraction`] → Correct: that spec already requires bytes pass-through; only `typed-api-client` needs the new fidelity requirement.

## Migration Plan

No data migration. Rollback is a plain revert of the two-line edit in `_fetch.py` plus the delta spec/tests. Public `HttpClient` API (`body_data: str | bytes | None`, `headers: dict[str,str] | None`) does not change; only internal fidelity improves.

## Open Questions

None.
