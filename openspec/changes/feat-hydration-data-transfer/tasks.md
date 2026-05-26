# Tasks: Hydration Data Transfer

## Task 1: Create hydration module with payload schema and serialization

**Estimated time:** 1.5 hours

Create the `webcompy/hydration/` package with:
- `webcompy/hydration/__init__.py` — Public API exports
- `webcompy/hydration/_payload.py` — `TransferPayload` dataclass, `TRANSFER_VERSION`, `TransferFetchEntry`, `TransferAsyncResultEntry`, `serialize_payload()` and `deserialize_payload()` functions
- `webcompy/hydration/_collect.py` — `collect_transfer_data()` function that gathers `AsyncResult` states and `FetchPort` response cache from the component tree

The payload schema:
```python
@dataclass
class TransferFetchEntry:
    status_code: int
    headers: dict[str, str]
    body: str

@dataclass
class TransferAsyncResultEntry:
    state: str  # "success"
    data: Any

@dataclass
class TransferPayload:
    __webcompy_transfer_version__: int = 1
    fetches: dict[str, TransferFetchEntry]
    async_results: dict[str, TransferAsyncResultEntry]
```

`serialize_payload()` produces HTML-escaped JSON string. `deserialize_payload()` parses JSON, validates version, and returns `TransferPayload | None` (None on parse error or version mismatch).

**Files created:** `webcompy/hydration/__init__.py`, `webcompy/hydration/_payload.py`, `webcompy/hydration/_collect.py`

---

## Task 2: Add response caching to ServerFetchPort

**Estimated time:** 1.5 hours

Modify `webcompy/ports/_server/_fetch.py` to add an internal response cache for self-site fetch requests:

- Add `_response_cache: dict[str, Response]` to `ServerFetchPort.__init__()`
- In `fetch()`, after a successful self-site request, cache the response keyed by URL (for GET) or by `f"{method}:{url}:{body}"` for non-GET requests
- If a cache hit occurs, return the cached response without making a network request
- Add `get_transfer_data() -> dict[str, dict]` method that returns the cache contents in transfer payload format (excluding external URL responses)
- Add `clear_cache()` method for cleanup between SSR renders
- Only cache responses from self-site URLs (those classified by `is_self_site_url()`)

**Files modified:** `webcompy/ports/_server/_fetch.py`, `webcompy/ports/_fetch.py` (add `is_self_site_url()` to `FetchPort` ABC — this may already exist from `feat/server-fetch-port-asgi`)

---

## Task 3: Add state restoration to AsyncResult

**Estimated time:** 2 hours

Modify `webcompy/aio/_async_result.py` to support state restoration from the transfer payload:

- Add `_restore_from_transfer(data: Any)` method to `AsyncResult` that:
  - Sets `_state.value = AsyncState.SUCCESS`
  - Sets `_data.value = data`
  - Sets `_error.value = None`
  - Skips `_execute()` — the async function is never called
- Modify `useAsyncResult` (in `webcompy/aio/`) to check the transfer payload before scheduling async execution:
  - If the component ID is found in the transfer payload `async_results` with `state == "success"`, call `_restore_from_transfer(data)` instead of scheduling execution
  - If not found, proceed with normal `PENDING` → `LOADING` → `SUCCESS/ERROR` lifecycle

The transfer payload needs to be accessible during component setup. Add a module-level `_transfer_payload` variable (or use DI) that is set during `app.run()` initialization and cleared after all restorations are complete.

**Files modified:** `webcompy/aio/_async_result.py`, `webcompy/aio/__init__.py`, possibly `webcompy/components/_component.py` (for component ID access during setup)

---

## Task 4: Add BrowserFetchPort cache population from transfer payload

**Estimated time:** 1.5 hours

Modify `webcompy/ports/_browser/_fetch.py` to populate an internal response cache from the transfer payload:

- Add `_response_cache: dict[str, Response]` to `BrowserFetchPort.__init__()`
- Add `populate_from_transfer(data: dict[str, dict])` method that converts transfer payload `fetches` entries into `Response` objects and stores them in `_response_cache`
- In `fetch()`, check `_response_cache` for matching URL before making a network request
- If a cache hit occurs, return the cached `Response` without calling `browser.fetch()`
- Cache entries persist for the lifetime of the `BrowserFetchPort` instance (no eviction)
- Add a key generation helper that matches `ServerFetchPort`'s key format for non-GET requests

**Files modified:** `webcompy/ports/_browser/_fetch.py`

---

## Task 5: Inject transfer payload into HTML output

**Estimated time:** 1.5 hours

Modify `webcompy/cli/_html.py` and `webcompy/app/_app.py` to inject the transfer payload into the HTML output:

- In `WebComPyApp` (or `AppDocumentRoot`), add a method `_collect_transfer_data() -> dict` that:
  - Retrieves `ServerFetchPort` from DI scope
  - Calls `server_fetch_port.get_transfer_data()`
  - Iterates over `ComponentStore.components` to find `AsyncResult` instances in `SUCCESS` state
  - Returns the combined transfer data dict
- In `generate_html()`, after rendering the app root:
  - Call `app._collect_transfer_data()` (or accept it as a parameter)
  - Serialize the data using `serialize_payload()`
  - Create a `<script type="application/json" id="__webcompy_data__">` element with the serialized payload
  - Insert it into the HTML output before the PyScript bootstrap `<script>` tag
- If `generate_html()` is called without an app (e.g., prerender=False), inject an empty payload

**Files modified:** `webcompy/cli/_html.py`, `webcompy/app/_app.py`, `webcompy/app/_root_component.py`

---

## Task 6: Restore transfer data during browser initialization

**Estimated time:** 2 hours

Modify `webcompy/app/_root_component.py` and `webcompy/app/_app.py` to restore transfer data during `app.run()`:

- In `app.run()`, before the first render:
  - Locate the `<script type="application/json" id="__webcompy_data__">` element in the DOM
  - Parse its content using `deserialize_payload()`
  - If the payload is valid:
    - Call `browser_fetch_port.populate_from_transfer(payload.fetches)` to populate the fetch cache
    - Set a module-level or app-level reference to `payload.async_results` for `AsyncResult` restoration
  - If the payload is missing or invalid, proceed with an empty payload
  - Remove the `<script>` element from the DOM after reading (to free memory)
- During component setup, `useAsyncResult` checks the transfer payload for a matching component ID
- After all component restorations, clear the `async_results` reference

**Files modified:** `webcompy/app/_app.py`, `webcompy/app/_root_component.py`, `webcompy/aio/_async_result.py` (integration with component IDs)

---

## Task 7: Write unit tests

**Estimated time:** 2 hours

Write unit tests for all new functionality:

- `tests/test_hydration_payload.py` — Test `TransferPayload` serialization/deserialization:
  - Valid payload with fetches and async_results
  - Empty payload (no data)
  - Payload with non-serializable data (excluded with warning)
  - HTML escaping of special characters
  - Unknown version rejection
  - Malformed JSON handling
- `tests/test_server_fetch_cache.py` — Test `ServerFetchPort` response caching:
  - Cache population on self-site GET request
  - Cache hit returns cached response
  - Cache miss makes network request
  - Non-GET request cache key includes method and body
  - External URLs are not cached
  - `get_transfer_data()` returns correct format
  - `clear_cache()` empties the cache
- `tests/test_async_result_restore.py` — Test `AsyncResult._restore_from_transfer()`:
  - Restoration sets state to SUCCESS with correct data
  - `is_success` and `is_loading` computed values are correct
  - Async function is NOT called after restoration
  - Missing component ID falls through to normal lifecycle
- `tests/test_browser_fetch_cache.py` — Test `BrowserFetchPort` cache population:
  - `populate_from_transfer()` creates `Response` objects from payload data
  - `fetch()` returns cached response without network request
  - `fetch()` makes network request for non-cached URLs
  - Cache persists across multiple fetches

**Files created:** `tests/test_hydration_payload.py`, `tests/test_server_fetch_cache.py`, `tests/test_async_result_restore.py`, `tests/test_browser_fetch_cache.py`

---

## Task 8: Write E2E tests for hydration data transfer

**Estimated time:** 2 hours

Write end-to-end tests that verify the full SSR→browser data transfer flow:

- Test that SSG output contains the `__webcompy_data__` script tag with resolved data
- Test that browser hydration reads the payload and restores `AsyncResult` states
- Test that browser-side `FetchPort.fetch()` returns cached responses from the payload
- Test that components with transferred `AsyncResult` data skip the loading phase
- Test that components not in the payload follow the normal async lifecycle
- Test that the payload is removed from the DOM after reading
- Test the full flow: SSR with async data → SSG output with payload → browser hydration with restored state

These tests use the existing E2E test infrastructure (Playwright + `webcompy inspect`).

**Files created:** E2E test script for hydration data transfer