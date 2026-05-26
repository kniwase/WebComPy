# Hydration Data Transfer

## Purpose

When a WebComPy application is pre-rendered on the server (SSG or SSR) and then hydrated in the browser, the browser currently re-executes all component setups from scratch. This means every `AsyncResult` that completed on the server triggers a new async fetch, and users see loading states for data that was already available in the server-rendered HTML. The hydration data transfer mechanism eliminates this redundancy by serializing resolved server-side state into the HTML and restoring it during browser-side hydration.

## ADDED Requirements

### Requirement: The transfer payload shall be embedded in the HTML output

After SSR rendering completes, the framework SHALL collect all resolved `AsyncResult` states and `FetchPort` response caches, serialize them into a JSON payload, and embed the payload in a `<script type="application/json" id="__webcompy_data__">` tag in the HTML output. The payload SHALL be placed at the end of the `<body>`, before the PyScript bootstrap script tag.

#### Scenario: Generating HTML with transfer payload
- **WHEN** `generate_html()` renders a page that includes async components with resolved data
- **THEN** the HTML output SHALL contain a `<script type="application/json" id="__webcompy_data__">` tag
- **AND** the tag content SHALL be a JSON object with a `__webcompy_transfer_version__` field set to `1`
- **AND** the tag SHALL appear after the app root element and before the PyScript bootstrap script

#### Scenario: Generating HTML with no async data
- **WHEN** `generate_html()` renders a page that includes no async components or no resolved data
- **THEN** the HTML output SHALL still contain a `<script type="application/json" id="__webcompy_data__">` tag
- **AND** the payload SHALL have empty `fetches` and `async_results` objects

#### Scenario: Payload is HTML-escaped
- **WHEN** resolved data contains characters that could be interpreted as HTML (e.g., `<script>`, `"`, `&`)
- **THEN** the payload SHALL be HTML-escaped before embedding in the `<script>` tag
- **AND** the browser SHALL correctly parse the escaped JSON without XSS vulnerability

### Requirement: The transfer payload shall include a version field

The payload JSON object SHALL include a `__webcompy_transfer_version__` field with an integer value indicating the payload format version. The current version SHALL be `1`.

#### Scenario: Version field is present
- **WHEN** the transfer payload is deserialized
- **THEN** the `__webcompy_transfer_version__` field SHALL be present
- **AND** its value SHALL be `1`

#### Scenario: Unknown version is rejected
- **WHEN** the transfer payload has a `__webcompy_transfer_version__` value that is not recognized by the deserializer
- **THEN** the payload SHALL be ignored entirely
- **AND** hydration SHALL proceed without transfer data (components will re-fetch)

### Requirement: The transfer payload shall serialize FetchPort response caches

`ServerFetchPort` SHALL maintain an internal response cache for all self-site fetch requests made during SSR rendering. After rendering completes, the cache SHALL be collected and included in the transfer payload under the `fetches` key. Each entry SHALL be keyed by the request URL and SHALL include `status_code`, `headers`, and `body`.

#### Scenario: Serializing a self-site fetch response
- **WHEN** a component calls `await fetch_port.fetch("/api/users")` during SSR
- **AND** the response has `status_code=200`, `headers={"content-type": "application/json"}`, and `body='[{"id": 1}]'`
- **THEN** the transfer payload `fetches` section SHALL contain the entry `"/api/users": {"status_code": 200, "headers": {"content-type": "application/json"}, "body": "[{\"id\": 1}]"}`
- **AND** external URL fetches SHALL NOT be included in the payload

#### Scenario: Multiple fetches to the same URL
- **WHEN** two components both call `await fetch_port.fetch("/api/users")` during SSR
- **THEN** only one entry for `/api/users` SHALL appear in the `fetches` section
- **AND** the response data SHALL be from the first fetch (subsequent fetches return cached response)

#### Scenario: No self-site fetches during SSR
- **WHEN** no `FetchPort.fetch()` calls were made during SSR
- **THEN** the `fetches` section SHALL be an empty object `{}`

### Requirement: The transfer payload shall serialize resolved AsyncResult states

After SSR rendering completes, all `AsyncResult` instances that reached `SUCCESS` state SHALL have their data collected and included in the transfer payload under the `async_results` key. Each entry SHALL be keyed by the component ID and SHALL include `state` and `data`.

#### Scenario: Serializing a resolved AsyncResult
- **WHEN** a component with ID `"my-component-abc123"` has an `AsyncResult` in `SUCCESS` state with `data.value = {"name": "Alice"}`
- **THEN** the transfer payload `async_results` section SHALL contain `"my-component-abc123": {"state": "success", "data": {"name": "Alice"}}`

#### Scenario: AsyncResult in LOADING or PENDING state
- **WHEN** a component's `AsyncResult` is in `LOADING` or `PENDING` state at the end of SSR rendering
- **THEN** the `AsyncResult` SHALL NOT be included in the `async_results` section
- **AND** the browser SHALL re-execute the async function normally

#### Scenario: AsyncResult in ERROR state
- **WHEN** a component's `AsyncResult` is in `ERROR` state at the end of SSR rendering
- **THEN** the `AsyncResult` SHALL NOT be included in the `async_results` section
- **AND** the browser SHALL re-execute the async function normally

#### Scenario: Non-JSON-serializable AsyncResult data
- **WHEN** an `AsyncResult`'s data contains non-JSON-serializable types (e.g., custom objects, datetime)
- **THEN** the entry SHALL be silently excluded from the `async_results` section
- **AND** a warning SHALL be logged indicating the component ID and the serialization failure

### Requirement: BrowserFetchPort shall use the transfer payload cache

During browser initialization, `BrowserFetchPort` SHALL read the transfer payload and populate an internal cache. When `fetch()` is called with a URL that matches a cached response, `BrowserFetchPort` SHALL return the cached response without making a network request.

#### Scenario: Fetch matches cached response
- **WHEN** a component calls `await fetch_port.fetch("/api/users")` in the browser
- **AND** `/api/users` is present in the transfer payload `fetches` section
- **THEN** `BrowserFetchPort` SHALL return a `Response` with the cached `status_code`, `headers`, and `body`
- **AND** no actual HTTP request SHALL be made

#### Scenario: Fetch does not match cached response
- **WHEN** a component calls `await fetch_port.fetch("/api/new-endpoint")` in the browser
- **AND** `/api/new-endpoint` is NOT present in the transfer payload `fetches` section
- **THEN** `BrowserFetchPort` SHALL make a normal HTTP request via `browser.fetch()`
- **AND** the response SHALL be returned as usual

#### Scenario: Cache entry is consumed after first use
- **WHEN** a component calls `await fetch_port.fetch("/api/users")` and the response is returned from cache
- **THEN** subsequent calls to `fetch_port.fetch("/api/users")` SHALL also return from cache
- **AND** the cache entry SHALL persist for the lifetime of the `BrowserFetchPort` instance

### Requirement: AsyncResult shall restore state from transfer payload

During browser initialization, `AsyncResult` instances SHALL check the transfer payload for matching component IDs. If a match is found with `state` equal to `"success"`, the `AsyncResult` SHALL restore directly to `SUCCESS` state with the transferred data, bypassing the `PENDING` → `LOADING` → `SUCCESS` lifecycle.

#### Scenario: AsyncResult restored from transfer payload
- **WHEN** a component with ID `"my-component-abc123"` is initialized in the browser
- **AND** the transfer payload `async_results` section contains `"my-component-abc123": {"state": "success", "data": {"name": "Alice"}}`
- **THEN** the `AsyncResult` SHALL have `state.value == AsyncState.SUCCESS`
- **AND** `data.value` SHALL be `{"name": "Alice"}`
- **AND** `is_success.value` SHALL be `True`
- **AND** `is_loading.value` SHALL be `False`
- **AND** the async function SHALL NOT be executed

#### Scenario: AsyncResult not found in transfer payload
- **WHEN** a component with ID `"new-component-xyz789"` is initialized in the browser
- **AND** the transfer payload `async_results` section does NOT contain `"new-component-xyz789"`
- **THEN** the `AsyncResult` SHALL follow the normal `PENDING` → `LOADING` → `SUCCESS/ERROR` lifecycle
- **AND** the async function SHALL be executed normally

#### Scenario: Transfer payload has stale component ID
- **WHEN** the transfer payload contains a component ID that no longer exists in the browser component tree
- **THEN** the stale entry SHALL be silently ignored
- **AND** no warning SHALL be logged (stale entries are expected during development when component trees change)

### Requirement: The transfer payload shall be read during browser initialization

`app.run()` SHALL read the transfer payload from the DOM before executing component setups. The payload SHALL be parsed and stored in a location accessible to `AsyncResult` and `BrowserFetchPort` for restoration.

#### Scenario: Reading the payload during app.run()
- **WHEN** `app.run()` is called in the browser
- **THEN** the framework SHALL locate the `<script type="application/json" id="__webcompy_data__">` element
- **AND** parse its content as JSON
- **AND** validate the `__webcompy_transfer_version__` field
- **AND** make the parsed payload available for `AsyncResult` restoration and `BrowserFetchPort` cache population

#### Scenario: Payload element is missing
- **WHEN** `app.run()` is called in the browser and no `<script type="application/json" id="__webcompy_data__">` element exists
- **THEN** the framework SHALL proceed with an empty transfer payload
- **AND** all `AsyncResult` instances SHALL follow the normal lifecycle
- **AND** `BrowserFetchPort` SHALL make normal network requests

#### Scenario: Payload is invalid JSON
- **WHEN** `app.run()` is called and the `<script>` element content cannot be parsed as JSON
- **THEN** the framework SHALL proceed with an empty transfer payload
- **AND** a warning SHALL be logged indicating the payload parse failure
- **AND** all `AsyncResult` instances SHALL follow the normal lifecycle

### Requirement: ServerFetchPort shall cache responses for transfer

`ServerFetchPort` SHALL cache all self-site fetch responses during SSR rendering. The cache SHALL be keyed by request URL (including method and body for non-GET requests). After rendering completes, the cache SHALL be collectible for inclusion in the transfer payload.

#### Scenario: Caching a self-site GET response
- **WHEN** `ServerFetchPort.fetch("/api/users")` is called during SSR
- **AND** the response is successful
- **THEN** the response SHALL be cached under the key `"/api/users"` (method defaults to GET)
- **AND** subsequent calls to `fetch("/api/users")` SHALL return the cached response

#### Scenario: Caching a self-site POST response
- **WHEN** `ServerFetchPort.fetch("/api/submit", method="POST", body='{"name": "Bob"}')` is called during SSR
- **THEN** the response SHALL be cached under a key that includes the method and body
- **AND** `fetch("/api/submit", method="POST", body='{"name": "Bob"}')` SHALL return the cached response
- **AND** `fetch("/api/submit")` (GET) SHALL NOT return the cached POST response

#### Scenario: Collecting the response cache
- **WHEN** `server_fetch_port.get_transfer_data()` is called after SSR rendering
- **THEN** it SHALL return a dict mapping URLs to `{"status_code": int, "headers": dict, "body": str}` entries
- **AND** external URL responses SHALL NOT be included (only self-site fetches are cached for transfer)

### Requirement: The transfer payload shall only include JSON-serializable data

Only JSON-serializable types (str, int, float, bool, None, list, dict) SHALL be included in the transfer payload. Non-serializable data SHALL be silently excluded.

#### Scenario: AsyncResult data is JSON-serializable
- **WHEN** an `AsyncResult` resolved with data `{"name": "Alice", "age": 30, "active": true}`
- **THEN** the data SHALL be included in the `async_results` section as-is

#### Scenario: AsyncResult data contains non-serializable types
- **WHEN** an `AsyncResult` resolved with a custom Python object (e.g., `datetime.date(2024, 1, 1)`)
- **THEN** the entry SHALL be excluded from the `async_results` section
- **AND** a warning SHALL be logged

#### Scenario: FetchPort response body is always a string
- **WHEN** a fetch response body is collected for transfer
- **THEN** the body SHALL be stored as a string (the raw response text)
- **AND** the string SHALL be JSON-serializable by definition