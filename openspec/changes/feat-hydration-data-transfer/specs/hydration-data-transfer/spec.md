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
- **AND** a warning SHALL be logged indicating the unrecognized schema version

#### Scenario: Missing version field
- **WHEN** the transfer payload does not contain a `__webcompy_transfer_version__` field
- **THEN** the payload SHALL be ignored entirely (treated as incompatible schema)
- **AND** hydration SHALL proceed without transfer data
- **AND** a warning SHALL be logged indicating the missing schema version

#### Scenario: Version matches but partial payload corruption
- **WHEN** the transfer payload has a valid `__webcompy_transfer_version__` but individual entries are malformed (e.g., `async_results` entry has wrong shape)
- **THEN** the malformed entry SHALL be silently skipped
- **AND** valid entries SHALL still be restored
- **AND** a warning SHALL be logged with the malformed entry key
- **AND** components associated with skipped entries SHALL follow the normal lifecycle (re-fetch, no crash)

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

### Requirement: Component IDs shall be deterministically generated for transfer matching

Component SHALL be assigned a deterministic `_component_id` at render time (during `_render()`) based on the component's position in the render tree. The `_component_id` is separate from the existing `_instance_id` (which is a UUID for instance identity) and is recomputed on each render to match the server-side tree structure. The `_component_id` formula SHALL be: `"<parent_id>/<type_name>/<sibling_index>"` where `parent_id` is the parent element's `_component_id` (or `"root"` for top-level components), `type_name` is the component's class name, and `sibling_index` is the 0-indexed position among siblings of the same parent. This forms a path through the component tree that is globally unique. For example, a component `MyPage` at the root with a child `DataCard` at sibling index 0 and a nested `AsyncBadge` at sibling index 1 would produce: `"root/MyPage/0"`, `"root/MyPage/0/DataCard/0"`, and `"root/MyPage/0/DataCard/0/AsyncBadge/1"`.

The `_component_id` SHALL be stored as a separate field (`_component_id: str | None`) on the `Component` class, distinct from `_instance_id`. It SHALL be computed during `_render()` (not `__init__()`) because the render tree position is only known once the component is placed in the tree. The ID is recomputed on each render cycle, so it reflects the current tree position.

**Transfer payload matching is best-effort, not guaranteed.** If the component tree structure differs between SSR and browser hydration (e.g., conditional rendering, Suspense fallback changes, `ClientOnly` boundary differences), component IDs will not match, and `AsyncResult` transfer SHALL gracefully fall back to the normal lifecycle. In particular, when a `Suspense` boundary renders fallback during SSR (because of timeout), **zero** descendant component IDs will match during browser hydration — the entire subtree has different structure. This is expected and documented: developers whose async data requires transfer to the browser SHALL ensure the SSR timeout is sufficient to resolve within the time budget, or accept that async state will be re-fetched in the browser.

#### Scenario: Same component tree produces same IDs on server and browser
- **WHEN** a component tree is rendered during SSR, producing component IDs for `AsyncResult` entries
- **AND** the same component tree is rendered during browser hydration
- **THEN** each component's `_component_id` SHALL be identical in both environments
- **AND** `async_results` entries in the transfer payload SHALL match the correct `AsyncResult` instances
- **AND** this stability is guaranteed by the hydration contract — `_hydrate_node()` adopts existing prerendered nodes, so the component tree structure in the browser matches the server exactly

#### Scenario: _component_id is computed during _render() not __init__()
- **WHEN** a `Component` is instantiated (before `_render()`)
- **THEN** `_component_id` SHALL be `None`
- **AND** during `_render()`, `_component_id` SHALL be computed from the component's current position in the render tree
- **AND** `_component_id` SHALL be recomputed on each `_render()` call to reflect the current tree position

#### Scenario: _component_id differs from _instance_id
- **WHEN** a component is instantiated
- **THEN** `_instance_id` SHALL be a UUID (random, unique per instance)
- **AND** `_component_id` SHALL be a deterministic path-based string (e.g., `"root/MyPage/0/DataCard/0"`)
- **AND** `_component_id` SHALL be recomputed on each render while `_instance_id` SHALL remain stable for the instance lifetime

#### Scenario: Component removal changes sibling indices for remaining components
- **WHEN** a component tree has 3 siblings at depth 2 (indices 0, 1, 2)
- **AND** on the browser side, sibling at index 1 is conditionally removed
- **THEN** the sibling at index 2 SHALL now have a different `_component_id` than in the server-side tree
- **AND** its `AsyncResult` SHALL NOT match the server-side entry (gracefully falls back to normal lifecycle)

### Requirement: AsyncResult shall restore state from transfer payload

During browser initialization, `AsyncResult` instances SHALL check the transfer payload for entry matching their owning component's deterministic `_component_id`. Because `_component_id` is computed during `_render()` (not `__init__()`), `useAsyncResult` called during component setup cannot immediately look up the transfer payload by component ID. To solve this timing problem: `AsyncResult` SHALL delay scheduling the async function until `_render()` time rather than executing during setup. During setup, `AsyncResult` SHALL store a reference to the owning component instance. At the start of `_render()`, `_component_id` is computed, `AsyncResult` looks up the transfer payload, and:
- If a match is found: `AsyncResult` SHALL restore directly to `SUCCESS` state from the transfer payload, and the async function SHALL NOT be scheduled.
- If no match: `AsyncResult` SHALL schedule the async function for execution as normal.

The async function SHALL NOT be scheduled during `__init__()` or `__setup__()` — it SHALL be deferred until `_render()` when `_component_id` is available. This ensures the transfer payload check happens before any async execution begins, eliminating the need to cancel in-progress async operations.

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

#### Scenario: Different component at same tree position in browser vs SSR
- **WHEN** component `ComponentA` renders at position `"MyPage/1/0"` during SSR and its `AsyncResult` data is included in the transfer payload
- **AND** a different component `ComponentB` renders at the same position `"MyPage/1/0"` during browser hydration (e.g., due to conditional rendering)
- **THEN** `_restore_from_transfer()` SHALL validate that the transferred data type is compatible with `ComponentB`'s expected `AsyncResult` type
- **AND** if incompatible, the entry SHALL be silently skipped and the component SHALL follow the normal lifecycle
- **AND** a `UserWarning` SHALL be logged indicating the type mismatch

#### Scenario: SSR resolves Suspense children within timeout — browser hydration matches component IDs
- **WHEN** a `Suspense` boundary resolves during SSR (children rendered, not fallback)
- **AND** the children's `_component_id` values are included in the transfer payload
- **THEN** during browser hydration, the same component tree SHALL produce the same `_component_id` values
- **AND** `AsyncResult` restoration SHALL succeed for components inside the resolved Suspense boundary
- **AND** the async function SHALL NOT be re-executed in the browser

#### Scenario: SSR renders Suspense fallback, browser renders children — component IDs differ
- **WHEN** a component inside `Suspense(fallback=..., children=lambda: AsyncDataComponent())` is rendered during SSR
- **AND** the async data does not resolve within the timeout, so fallback is rendered instead
- **THEN** the component's `_component_id` SHALL NOT appear in the SSR component tree (the fallback subtree replaces it)
- **AND** the `async_results` section of the transfer payload SHALL NOT contain an entry for that component
- **WHEN** browser hydration renders `children` instead of `fallback`
- **THEN** the component's `_component_id` SHALL be generated from its position in the browser-side tree
- **AND** this `_component_id` SHALL differ from what it would have been during SSR (the component tree structures are different: fallback subtree during SSR, children subtree during browser hydration)
- **AND** the component SHALL follow the normal `PENDING` → `LOADING` → `SUCCESS/ERROR` lifecycle (no transfer match because the SSR tree never contained this component)

### Requirement: The transfer payload shall be read during browser initialization

`app.run()` SHALL read the transfer payload from the DOM before executing component setups. The parsed payload SHALL be provided into the root DI scope via `provide(HYDRATION_DATA_KEY, payload)` before any component setup begins. This makes the payload accessible to `inject(HYDRATION_DATA_KEY)` calls during both component initialization and hydration phases. `AsyncResult` restoration and `BrowserFetchPort` cache population SHALL read from this DI-provided payload.

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

#### Scenario: Caching a self-site POST response with dict body
- **WHEN** `ServerFetchPort.fetch("/api/submit", method="POST", body={"name": "Bob"})` is called during SSR
- **THEN** the response SHALL be cached under the key `POST:/api/submit:{"name":"Bob"}` (json.dumps with sort_keys)
- **AND** `fetch("/api/submit", method="POST", body={"name": "Bob"})` SHALL return the cached response
- **AND** `fetch("/api/submit")` (GET) SHALL NOT return the cached POST response

#### Scenario: Unknown type tag during deserialization
- **WHEN** the transfer payload contains an unrecognized type tag (e.g., `{"__custom__": "value"}`)
- **THEN** the dict SHALL be left as-is without tag removal (passed through as a plain dict)
- **AND** a warning SHALL be logged indicating the unknown type tag

#### Scenario: Known type tag with invalid data
- **WHEN** the transfer payload contains a known type tag with malformed data (e.g., `{"__datetime__": "not-a-datetime"}`)
- **THEN** the entry SHALL be treated as a regular dict (not deserialized to the target type)
- **AND** a warning SHALL be logged identifying the malformed entry
- **AND** the component SHALL follow the normal lifecycle (no crash)

#### Scenario: Collecting the response cache
- **WHEN** `server_fetch_port.get_transfer_data()` is called after SSR rendering
- **THEN** it SHALL return a dict mapping URLs to `{"status_code": int, "headers": dict, "body": str}` entries
- **AND** external URL responses SHALL NOT be included (only self-site fetches are cached for transfer)

### Requirement: The transfer payload shall support extended types via tagged encoding

The serialization SHALL support `datetime.datetime`, `datetime.date`, `bytes`, and nested dict/list structures beyond the basic JSON types (`str`, `int`, `float`, `bool`, `None`, `list`, `dict`). These extended types SHALL be encoded with type tags as follows:

- **`datetime.datetime`**: Encoded as a dict with `__datetime__` tag containing an ISO 8601 string. When parsed, SHALL reconstruct the original `datetime.datetime` object with microsecond precision and UTC timezone.
- **`datetime.date`**: Encoded as a dict with `__date__` tag containing an ISO 8601 date string (`YYYY-MM-DD`). When parsed, SHALL reconstruct the original `datetime.date` object.
- **`bytes`**: Encoded as a dict with `__bytes__` tag containing a base64-encoded string. When parsed, SHALL reconstruct the original `bytes` object.
- **Nested dict/list**: Standard JSON dict/list serialization with extended type tags applied recursively at any nesting depth.

#### Scenario: Serializing datetime.datetime
- **WHEN** an `AsyncResult` resolves with data containing `{"created_at": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)}`
- **THEN** the serialized payload SHALL contain `"created_at": {"__datetime__": "2024-01-15T10:30:00+00:00"}`
- **AND** after deserialization, `created_at` SHALL be a `datetime.datetime` object equal to the original

#### Scenario: Serializing datetime.date
- **WHEN** an `AsyncResult` resolves with data containing `{"event_date": datetime.date(2024, 3, 20)}`
- **THEN** the serialized payload SHALL contain `"event_date": {"__date__": "2024-03-20"}`
- **AND** after deserialization, `event_date` SHALL be a `datetime.date` object equal to the original

#### Scenario: Serializing bytes
- **WHEN** an `AsyncResult` resolves with data containing `{"file_hash": b"\x01\x02\x03"}`
- **THEN** the serialized payload SHALL contain `"file_hash": {"__bytes__": "AQID"}`
- **AND** after deserialization, `file_hash` SHALL be a `bytes` object equal to the original

#### Scenario: Serializing nested structures with extended types
- **WHEN** an `AsyncResult` resolves with `{"items": [{"updated": datetime.datetime(...)}, {"name": "static"}]}`
- **THEN** `"{"updated": {"__datetime__": "..."}}` SHALL appear at the correct nested path
- **AND** `"{"name": "static"}` SHALL remain as a plain dict
- **AND** both SHALL be at the correct indices in the `items` list

#### Scenario: Unknown type tag during deserialization
- **WHEN** the transfer payload contains an unrecognized type tag (e.g., `{"__custom__": "value"}`)
- **THEN** the dict SHALL be left as-is without tag removal (passed through as a plain dict)
- **AND** a warning SHALL be logged indicating the unknown type tag