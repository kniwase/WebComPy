# Hydration Data Transfer

## Purpose

WebComPy currently re-executes all component setups in the browser during hydration, re-fetching data that was already resolved on the server. This causes duplicate network requests, a flash of loading states for data that was already available in the server-rendered HTML, and a visible content flicker for Signal-derived UI.

This change introduces a server-to-browser data transfer mechanism. The `ServerFetchPort` caches self-site responses during SSR. Resolved `AsyncResult` states are collected from the component tree. The combined data is serialized as a JSON payload embedded in a `<script type="application/json" id="__webcompy_data__">` tag in the SSR/SSG output. During browser hydration, `app.run()` reads the payload and:

- Populates `BrowserFetchPort`'s response cache (so duplicate `fetch()` calls return cached responses without network I/O).
- Provides the `async_results` section via a new `HYDRATION_DATA_KEY` DI key, so `use_async_result` can restore resolved states without re-executing the async function.

The result: components with transferred data skip the `LOADING` phase entirely on the client, eliminating duplicate fetches and the flash of loading states.

## ADDED Requirements

### Requirement: HYDRATION_DATA_KEY shall be a typed DI key

`HYDRATION_DATA_KEY: InjectKey[dict[str, Any]]` SHALL be defined in `packages/webcompy/src/webcompy/di/_keys.py` and exported from `packages/webcompy/src/webcompy/di/__init__.py`. The value SHALL be the `async_results` section of the transfer payload (a mapping from component ID to `TransferAsyncResultEntry`).

#### Scenario: HYDRATION_DATA_KEY is importable
- **WHEN** a developer writes `from webcompy.di import HYDRATION_DATA_KEY`
- **THEN** the import SHALL succeed
- **AND** `HYDRATION_DATA_KEY` SHALL be usable as the first argument to `inject()`

### Requirement: has_resolved_data() shall query the transfer payload

`has_resolved_data(component_id: str) -> bool` SHALL be defined in `packages/webcompy/src/webcompy/hydration/__init__.py` and SHALL return `True` when the transfer payload contains a resolved `AsyncResult` entry for the given component ID, and `False` otherwise (including when the payload is missing).

#### Scenario: has_resolved_data returns True for a transferred component
- **WHEN** `HYDRATION_DATA_KEY` is provided with a payload containing `{"component-1": TransferAsyncResultEntry(...)}`
- **AND** `has_resolved_data("component-1")` is called
- **THEN** the return value SHALL be `True`

#### Scenario: has_resolved_data returns False for a missing component
- **WHEN** `HYDRATION_DATA_KEY` is provided with a payload that does not contain `"component-x"`
- **AND** `has_resolved_data("component-x")` is called
- **THEN** the return value SHALL be `False`

#### Scenario: has_resolved_data returns False when payload is missing
- **WHEN** `HYDRATION_DATA_KEY` is not provided in the DI scope
- **AND** `has_resolved_data("any-id")` is called
- **THEN** the return value SHALL be `False`
- **AND** no exception SHALL be raised (the default is `None`)

### Requirement: TransferPayload shall define the payload schema

`TransferPayload` SHALL be a dataclass defined in `packages/webcompy/src/webcompy/hydration/_payload.py` with the following fields: `__webcompy_transfer_version__: int` (default `1`), `fetches: dict[str, TransferFetchEntry]`, and `async_results: dict[str, TransferAsyncResultEntry]`. `TransferFetchEntry` SHALL be a dataclass with `status_code: int`, `headers: dict[str, str]`, and `body: str`. `TransferAsyncResultEntry` SHALL be a dataclass with `state: str` (always `"success"` in this version) and `data: Any`.

#### Scenario: TransferPayload fields are exposed
- **WHEN** a developer creates a `TransferPayload`
- **THEN** the fields `__webcompy_transfer_version__`, `fetches`, and `async_results` SHALL be accessible as attributes
- **AND** the default value for `__webcompy_transfer_version__` SHALL be `1`

### Requirement: serialize_payload shall produce HTML-escaped JSON

`serialize_payload(payload: TransferPayload) -> str` SHALL convert the payload to a JSON object, HTML-escape the result to prevent XSS, and return the escaped string suitable for embedding inside a `<script>` tag. Non-JSON-serializable data SHALL be excluded with a warning logged.

#### Scenario: Serializing a payload with data
- **WHEN** a `TransferPayload` contains fetches and async_results
- **AND** `serialize_payload(payload)` is called
- **THEN** the return value SHALL be a valid JSON string
- **AND** special characters (`<`, `>`, `&`, `"`) in the data SHALL be HTML-escaped

#### Scenario: Serializing a payload with non-serializable data
- **WHEN** a `TransferAsyncResultEntry.data` field contains a value that is not JSON-serializable
- **THEN** the entry SHALL be excluded from the serialized payload
- **AND** a warning SHALL be logged

### Requirement: deserialize_payload shall validate version and parse JSON

`deserialize_payload(text: str) -> TransferPayload | None` SHALL parse the input as JSON, validate the `__webcompy_transfer_version__` field equals `1`, and return a `TransferPayload` on success or `None` on parse error, missing version, or unknown version.

#### Scenario: Deserializing a valid payload
- **WHEN** a valid JSON string with `__webcompy_transfer_version__: 1` is passed
- **THEN** a `TransferPayload` SHALL be returned with the parsed fields

#### Scenario: Deserializing an unknown version
- **WHEN** a JSON string with `__webcompy_transfer_version__: 999` is passed
- **THEN** the return value SHALL be `None`

#### Scenario: Deserializing malformed JSON
- **WHEN** a malformed JSON string is passed
- **THEN** the return value SHALL be `None`
- **AND** no exception SHALL propagate to the caller

### Requirement: ServerFetchPort shall cache self-site responses

`ServerFetchPort.fetch()` SHALL cache responses for self-site URLs (those classified by `is_self_site_url()`) keyed by URL for GET requests and by `f"{method}:{url}:{body}"` for non-GET requests. On a cache hit, the cached `Response` SHALL be returned without making a network request. External URL responses SHALL NOT be cached.

#### Scenario: Self-site GET response is cached
- **WHEN** `ServerFetchPort.fetch("/api/data")` is called for the first time
- **THEN** the network request SHALL be made
- **AND** the response SHALL be stored in `_response_cache["/api/data"]`

#### Scenario: Self-site GET cache hit
- **WHEN** `ServerFetchPort.fetch("/api/data")` is called a second time
- **THEN** the cached response SHALL be returned
- **AND** no network request SHALL be made

#### Scenario: External URL is not cached
- **WHEN** `ServerFetchPort.fetch("https://example.com/foo")` is called
- **THEN** the network request SHALL be made
- **AND** the response SHALL NOT be stored in the cache

#### Scenario: clear_cache empties the response cache
- **WHEN** `ServerFetchPort.clear_cache()` is called
- **THEN** the next fetch for a cached URL SHALL miss the cache and make a network request

### Requirement: ServerFetchPort shall expose transfer data

`ServerFetchPort.get_transfer_data() -> dict[str, TransferFetchEntry]` SHALL return the cache contents in transfer payload format. External URL responses SHALL be excluded.

#### Scenario: get_transfer_data returns only self-site responses
- **WHEN** the cache contains both self-site and external responses
- **AND** `get_transfer_data()` is called
- **THEN** the returned dict SHALL contain only self-site URL entries
- **AND** the format SHALL match `TransferFetchEntry`

### Requirement: AsyncResult shall support state restoration

`AsyncResult._restore_from_transfer(data: Any)` SHALL set `_state.value` to `AsyncState.SUCCESS`, set `_data.value` to `data`, and set `_error.value` to `None` without invoking the original async function. The `LOADING` state SHALL NOT be observed.

#### Scenario: Restoration sets state to SUCCESS
- **WHEN** `AsyncResult._restore_from_transfer(data)` is called
- **THEN** `_state.value` SHALL be `AsyncState.SUCCESS`
- **AND** `_data.value` SHALL be `data`
- **AND** `_error.value` SHALL be `None`

#### Scenario: Restoration does not call the async function
- **WHEN** `AsyncResult._restore_from_transfer(data)` is called
- **THEN** the original async function passed to `use_async_result` SHALL NOT be invoked
- **AND** no `LOADING` state SHALL be observed

### Requirement: use_async_result shall check the transfer payload first

`use_async_result` SHALL consult `HYDRATION_DATA_KEY` via `inject(HYDRATION_DATA_KEY, default={})` before scheduling async execution. If the component ID (the component's tree-position path identifier, `component._tree_path_id`) is found in the payload with `state == "success"`, the function SHALL call `_restore_from_transfer(data)` and skip execution. If not found, the function SHALL proceed with the normal `PENDING → LOADING → SUCCESS/ERROR` lifecycle.

#### Scenario: use_async_result restores from payload
- **WHEN** `use_async_result` is called inside a component setup function
- **AND** `HYDRATION_DATA_KEY` is provided with a payload containing the component's ID with `state == "success"`
- **THEN** the `AsyncResult` SHALL be set to `SUCCESS` with the transferred data
- **AND** the async function SHALL NOT be called

#### Scenario: use_async_result falls through to normal lifecycle
- **WHEN** `use_async_result` is called inside a component setup function
- **AND** the component ID is not in the transfer payload
- **THEN** the normal `PENDING → LOADING → SUCCESS/ERROR` lifecycle SHALL run
- **AND** the async function SHALL be executed

### Requirement: BrowserFetchPort shall populate cache from transfer

`BrowserFetchPort.populate_from_transfer(data: dict[str, TransferFetchEntry])` SHALL convert each `TransferFetchEntry` into a `Response` object and store it in the internal response cache. In `BrowserFetchPort.fetch()`, the cache SHALL be checked for matching URL before making a network request. On a hit, the cached `Response` SHALL be returned without calling `browser.fetch()`.

#### Scenario: populate_from_transfer caches responses
- **WHEN** `populate_from_transfer({"https://api/foo": TransferFetchEntry(...)})` is called
- **THEN** the cache SHALL contain a `Response` for `"https://api/foo"`
- **AND** `fetch("https://api/foo")` SHALL return the cached response without calling `browser.fetch()`

#### Scenario: Cache miss makes a network request
- **WHEN** `fetch("https://api/not-cached")` is called and the URL is not in the cache
- **THEN** `browser.fetch()` SHALL be called
- **AND** the response SHALL be returned to the caller

### Requirement: generate_html shall inject the transfer payload

`generate_html()` SHALL, after rendering the app root, call `app._collect_transfer_data()`, serialize the result using `serialize_payload()`, create a `<script type="application/json" id="__webcompy_data__">{escaped}</script>` element, and insert the script tag at the end of the `<body>`, before the PyScript bootstrap `<script>` tag. If `generate_html()` is called without an app, the script tag SHALL be omitted.

#### Scenario: SSG output contains the data script tag
- **WHEN** `webcompy generate` produces an HTML file
- **THEN** the HTML SHALL contain `<script type="application/json" id="__webcompy_data__">{...}</script>` at the end of the body
- **AND** the script content SHALL be valid JSON
- **AND** the script content SHALL be HTML-escaped

### Requirement: app.run shall restore transfer data

`app.run()` SHALL, before the first render, locate the `<script type="application/json" id="__webcompy_data__">` element in the DOM, parse its content using `deserialize_payload()`, and if the payload is valid, call `browser_fetch_port.populate_from_transfer(payload.fetches)` and provide `payload.async_results` via `HYDRATION_DATA_KEY` in the root DI scope. If the payload is missing or invalid, the function SHALL proceed with an empty payload. The script element SHALL be removed from the DOM after reading.

#### Scenario: Valid payload is restored during app.run
- **WHEN** `app.run()` is called and the DOM contains a valid `__webcompy_data__` script tag
- **THEN** `BrowserFetchPort.populate_from_transfer()` SHALL be called with the `fetches` section
- **AND** `HYDRATION_DATA_KEY` SHALL be provided with the `async_results` section

#### Scenario: Missing payload proceeds with empty data
- **WHEN** `app.run()` is called and the DOM does not contain a `__webcompy_data__` script tag
- **THEN** the `BrowserFetchPort` cache SHALL be empty
- **AND** `HYDRATION_DATA_KEY` SHALL NOT be provided
- **AND** components SHALL use the normal `PENDING → LOADING → SUCCESS` lifecycle

#### Scenario: Script tag is removed after reading
- **WHEN** `app.run()` has read the `__webcompy_data__` script tag
- **THEN** the script tag SHALL be removed from the DOM

### Requirement: AppDocumentRoot shall collect transfer data

`AppDocumentRoot` (or `WebComPyApp`) SHALL provide a `_collect_transfer_data() -> TransferPayload` method that retrieves `ServerFetchPort` from the DI scope, calls `server_fetch_port.get_transfer_data()`, and iterates over `ComponentStore.components` to find `AsyncResult` instances in `SUCCESS` state with a `component_id` matching the instance's `_tree_path_id`.

#### Scenario: Transfer data is collected after SSR render
- **WHEN** `_collect_transfer_data()` is called after a successful SSR render
- **THEN** the returned payload SHALL contain entries for all `ServerFetchPort` self-site cache hits
- **AND** the returned payload SHALL contain entries for all `AsyncResult` instances in `SUCCESS` state

## Limitations

Signal values are not transferred. Only `AsyncResult` states and `FetchPort` response caches are transferred. Application-level `Signal` values computed during SSR are not serialized. Components that derive UI state directly from `Signal` values may still experience a flash of default values during hydration. Developers SHOULD use `Suspense` or `ClientOnly` boundaries to manage the transition for Signal-derived state. Full `Signal` value transfer is deferred to a future change.
