# Hydration Data Transfer

## Purpose

WebComPy currently re-executes all component setups in the browser during hydration, re-fetching data that was already resolved on the server. This causes duplicate network requests, a flash of loading states for data that was already available in the server-rendered HTML, and a visible content flicker for Signal-derived UI.

This change introduces a server-to-browser data transfer mechanism. The `ServerFetchPort` caches self-site responses during SSR. Resolved `AsyncResult` states are collected from the component tree. The combined data is serialized as a JSON payload embedded in a `<script type="application/json" id="__webcompy_data__">` tag in the SSR/SSG output. During browser hydration, `app.run()` reads the payload and:

- Populates `BrowserFetchPort`'s response cache (so duplicate `fetch()` calls return cached responses without network I/O).
- Provides the `async_results` section via a new `HYDRATION_DATA_KEY` DI key, so `use_async_result` can restore resolved states without re-executing the async function.

The result: components with transferred data skip the `LOADING` phase entirely on the client, eliminating duplicate fetches and the flash of loading states.

## Requirements

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

### Requirement: TransferPayload shall include fetches, async_results, signals, and resources

`TransferPayload` SHALL be a dataclass defined in `packages/webcompy/src/webcompy/hydration/_payload.py` with the following fields: `__webcompy_transfer_version__: int` (default `3`), `fetches: dict[str, TransferFetchEntry]`, `async_results: dict[str, TransferAsyncResultEntry]`, `signals: dict[str, dict[str, Any]]`, and `resources: dict[str, str]` (base64-encoded bytes keyed by package-relative POSIX path). The `signals` field maps component ID to a dict of `{attr_name: encoded_value}` where encoded values are produced by `encode()` from `webcompy.hydration._codec`. `TransferFetchEntry` SHALL be a dataclass with `status_code: int`, `headers: dict[str, str]`, and `body: str`. `TransferAsyncResultEntry` SHALL be a dataclass with `state: str` (always `"success"` in this version) and `data: Any`.

`deserialize_payload()` SHALL accept versions 1, 2, and 3. v1 payloads are treated as having empty `signals` and `resources` dicts. v2 payloads have `signals` populated but empty `resources`. v3 payloads have all fields populated. Unknown versions SHALL be rejected.

#### Scenario: TransferPayload fields are exposed
- **WHEN** a developer creates a `TransferPayload`
- **THEN** the fields `__webcompy_transfer_version__`, `fetches`, `async_results`, `signals`, and `resources` SHALL be accessible as attributes
- **AND** the default value for `__webcompy_transfer_version__` SHALL be `3`

#### Scenario: Serializing a version 3 payload
- **WHEN** `serialize_payload()` is called with a `TransferPayload` containing signals and resources
- **THEN** the JSON output SHALL include `"__webcompy_transfer_version__": 3`
- **AND** the `"signals"` and `"resources"` keys SHALL be present in the output

#### Scenario: Deserializing a version 3 payload
- **WHEN** `deserialize_payload()` receives a version 3 JSON string
- **THEN** the resulting `TransferPayload` SHALL have the `signals` and `resources` dicts populated from the JSON

#### Scenario: Deserializing a version 2 payload (backward compatibility)
- **WHEN** `deserialize_payload()` receives a version 2 JSON string (no `resources` key)
- **THEN** the resulting `TransferPayload.signals` SHALL be populated from the JSON
- **AND** the resulting `TransferPayload.resources` SHALL be an empty dict `{}`

#### Scenario: Deserializing a version 1 payload (backward compatibility)
- **WHEN** `deserialize_payload()` receives a version 1 JSON string (no `signals` or `resources` key)
- **THEN** the resulting `TransferPayload.signals` SHALL be an empty dict `{}`
- **AND** the resulting `TransferPayload.resources` SHALL be an empty dict `{}`
- **AND** no error SHALL be raised

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

`deserialize_payload(text: str) -> TransferPayload | None` SHALL parse the input as JSON, validate the `__webcompy_transfer_version__` field against the accept-list `{1, 2, 3}`, and return a `TransferPayload` on success or `None` on parse error, missing version, or unknown version.

#### Scenario: Deserializing a valid v1 payload
- **WHEN** a valid JSON string with `__webcompy_transfer_version__: 1` is passed
- **THEN** a `TransferPayload` SHALL be returned with the parsed fields
- **AND** the `signals` and `resources` fields SHALL default to empty dicts `{}`

#### Scenario: Deserializing a valid v2 payload
- **WHEN** a valid JSON string with `__webcompy_transfer_version__: 2` is passed
- **THEN** a `TransferPayload` SHALL be returned with `fetches`, `async_results`, and `signals` populated from the JSON
- **AND** the `resources` field SHALL default to an empty dict `{}`

#### Scenario: Deserializing a valid v3 payload
- **WHEN** a valid JSON string with `__webcompy_transfer_version__: 3` is passed
- **THEN** a `TransferPayload` SHALL be returned with `fetches`, `async_results`, `signals`, and `resources` populated from the JSON

#### Scenario: Deserializing an unknown version
- **WHEN** a JSON string with `__webcompy_transfer_version__: 999` is passed
- **THEN** the return value SHALL be `None`

#### Scenario: Deserializing malformed JSON
- **WHEN** a malformed JSON string is passed
- **THEN** the return value SHALL be `None`
- **AND** no exception SHALL propagate to the caller

### Requirement: TransferPayload serialization shall use the codec engine

`serialize_payload()` SHALL apply `encode()` from `webcompy.hydration._codec` to `TransferAsyncResultEntry.data` and `TransferFetchEntry.body` before `json.dumps()`. `deserialize_payload()` SHALL apply `decode()` after `json.loads()`. The `__webcompy_transfer_version__` field SHALL remain `1` for payloads without the `signals` section (Signal value transfer, which adds the `signals` section and bumps to version 2, is a separate change). The codec is version-agnostic and works with both v1 and v2 payloads.

Non-serializable values that fail even the codec's extended encoders SHALL be dropped with a warning (consistent with the existing `_try_serialize_value` behavior), preserving the best-effort transfer philosophy.

#### Scenario: AsyncResult data with datetime is transferred correctly
- **WHEN** an `AsyncResult` resolves to a value containing a `datetime` during SSR
- **AND** `serialize_payload()` is called
- **THEN** the datetime SHALL be encoded via the codec as a type-tagged dict `{"__webcompy_type__": "datetime", "__webcompy_value__": "..."}`
- **AND** the browser-side `deserialize_payload()` SHALL reconstruct the `datetime` instance via `decode()`

#### Scenario: AsyncResult data with a dataclass is transferred correctly
- **WHEN** an `AsyncResult` resolves to a dataclass instance during SSR
- **AND** `serialize_payload()` is called
- **THEN** the dataclass SHALL be encoded via the codec with module, class name, and field values
- **AND** the browser-side `deserialize_payload()` SHALL reconstruct the dataclass instance via `importlib.import_module` and `cls(**fields)`

#### Scenario: Non-serializable value failing the codec is dropped
- **WHEN** an `AsyncResult` resolves to a value that the codec cannot encode (e.g., a file handle or socket object)
- **AND** `serialize_payload()` is called
- **THEN** the entry SHALL be dropped from the payload
- **AND** a warning SHALL be logged

#### Scenario: Backward compatibility with plain JSON AsyncResult data
- **WHEN** an `AsyncResult` resolves to a plain JSON-native value (e.g., `{"name": "Alice"}`)
- **AND** `serialize_payload()` is called
- **THEN** the value SHALL pass through the codec unchanged (no type tags added)
- **AND** the encoded output SHALL be identical to the previous `json.dumps` output

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

`use_async_result` SHALL consult `HYDRATION_DATA_KEY` via `inject(HYDRATION_DATA_KEY, default=None)` before scheduling async execution, but only while the initial hydration window is open (see "app.run shall restore transfer data" for the window definition). If the component's per-instance transfer id (see the `signal-value-transfer` capability) is found in the payload with `state == "success"`, the function SHALL call `_restore_from_transfer(data)` and skip execution. If not found, or if the hydration window has closed (e.g., client-side navigation), the function SHALL proceed with the normal `PENDING → LOADING → SUCCESS/ERROR` lifecycle — even if the payload contains an entry for the same component name.

#### Scenario: use_async_result restores from payload
- **WHEN** `use_async_result` is called inside a component setup function during the initial hydration window
- **AND** `HYDRATION_DATA_KEY` is provided with a payload containing the component instance's transfer id with `state == "success"`
- **THEN** the `AsyncResult` SHALL be set to `SUCCESS` with the transferred data
- **AND** the async function SHALL NOT be called

#### Scenario: use_async_result falls through to normal lifecycle
- **WHEN** `use_async_result` is called inside a component setup function
- **AND** the component's transfer id is not in the transfer payload
- **THEN** the normal `PENDING → LOADING → SUCCESS/ERROR` lifecycle SHALL run
- **AND** the async function SHALL be executed

#### Scenario: use_async_result does not restore after the hydration window closed
- **WHEN** `use_async_result` is called inside a component setup function during client-side navigation
- **AND** the initial page's payload contains an entry for the same component name
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

`app.run()` SHALL, before the first render, locate the `<script type="application/json" id="__webcompy_data__">` element in the DOM, parse its content using `deserialize_payload()`, and if the payload is valid:
1. Call `browser_fetch_port.populate_from_transfer(payload.fetches)`
2. Provide `payload.async_results` via `HYDRATION_DATA_KEY` in the root DI scope
3. Provide `payload.signals` via `HYDRATION_SIGNAL_DATA_KEY` in the root DI scope
4. Provide `payload.resources` via `RESOURCE_DATA_KEY` in the root DI scope

The `HYDRATION_SIGNAL_DATA_KEY` and `RESOURCE_DATA_KEY` SHALL be provided **before** any component creation, so that `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composable calls during component setup can access the payload via `inject(HYDRATION_SIGNAL_DATA_KEY)`, and `BrowserResourcePort` can access embedded resources via `inject(RESOURCE_DATA_KEY)`.

The `HYDRATION_DATA_KEY` and `HYDRATION_SIGNAL_DATA_KEY` payloads SHALL be valid only during the initial hydration window: the window opens before the initial render pass creates or hydrates the component tree and closes when the initial render pass (including the render-task drain that gates the hydration reveal) completes, whether it succeeds or fails. Component setups running after the window closes SHALL NOT restore from these payloads. The fetch-port response cache (`populate_from_transfer`) and `RESOURCE_DATA_KEY` are URL- and path-keyed respectively and are NOT subject to this lifecycle; they remain available for the app's lifetime. The `AppDocumentRoot` render pass SHALL resolve its render context as `_active_app_context`, falling back to the per-app `_render_context_cv` and then the module-level `_app_instance` fallback, so the window closes and the drain runs even when the render task does not carry `ContextVar` propagation (e.g., a PyScript JavaScript-originated callback).

If the payload is missing or invalid, the function SHALL proceed with an empty payload (all DI keys unprovided). The script element SHALL be removed from the DOM after reading.

#### Scenario: Valid payload is restored during app.run
- **WHEN** `app.run()` is called and the DOM contains a valid `__webcompy_data__` script tag
- **THEN** `BrowserFetchPort.populate_from_transfer()` SHALL be called with the `fetches` section
- **AND** `HYDRATION_DATA_KEY` SHALL be provided with the `async_results` section
- **AND** `HYDRATION_SIGNAL_DATA_KEY` SHALL be provided with the `signals` section
- **AND** `RESOURCE_DATA_KEY` SHALL be provided with the `resources` section
- **AND** all DI keys SHALL be available during component `__setup()`

#### Scenario: Missing payload proceeds with empty data
- **WHEN** `app.run()` is called and the DOM does not contain a `__webcompy_data__` script tag
- **THEN** the `BrowserFetchPort` cache SHALL be empty
- **AND** `HYDRATION_DATA_KEY` SHALL NOT be provided
- **AND** `HYDRATION_SIGNAL_DATA_KEY` SHALL NOT be provided
- **AND** `RESOURCE_DATA_KEY` SHALL NOT be provided
- **AND** components SHALL use the normal lifecycle (factories run, async functions execute)

#### Scenario: Script tag is removed after reading
- **WHEN** `app.run()` has read the `__webcompy_data__` script tag
- **THEN** the script tag SHALL be removed from the DOM

#### Scenario: Signal data available during setup
- **WHEN** a component's setup function calls `use_state(lambda: 0)`
- **AND** `HYDRATION_SIGNAL_DATA_KEY` was provided by `app.run()`
- **THEN** `inject(HYDRATION_SIGNAL_DATA_KEY)` SHALL return the signals payload
- **AND** `use_state()` SHALL check the payload for a matching key before running the factory

#### Scenario: Signal payload is closed after initial hydration
- **WHEN** the initial hydration render pass has completed
- **AND** a new component instance's setup calls `use_state()` (e.g., after client-side navigation)
- **THEN** `use_state()` SHALL NOT restore from `HYDRATION_SIGNAL_DATA_KEY`
- **AND** the factory SHALL run

#### Scenario: Payload closes even when the initial render fails
- **WHEN** the initial hydration render pass raises an error
- **THEN** the hydration payload SHALL be closed
- **AND** subsequent component setups SHALL NOT restore from `HYDRATION_SIGNAL_DATA_KEY` or `HYDRATION_DATA_KEY`

### Requirement: collect_transfer_data shall collect fetches, async_results, signals, and resources

`collect_transfer_data(root)` SHALL traverse the component tree and populate four sections of the `TransferPayload`: `fetches` (from `FetchPort.get_transfer_data()`), `async_results` (from `Component._async_results`), `signals` (from `Component.__signal_members__`), and `resources` (from `ResourcePort.get_recorded_resources()`). Signal values SHALL be encoded via `encode()` from `webcompy.hydration._codec`. Non-serializable Signal values SHALL be dropped with a warning. Resource content bytes SHALL be base64-encoded for transfer. Component-keyed sections (`async_results`, `signals`) SHALL use each component's per-instance transfer id as the key, so multiple instances of the same component produce distinct entries. `AppDocumentRoot` (or `WebComPyApp`) SHALL provide a `_collect_transfer_data() -> TransferPayload` method that wraps `collect_transfer_data(self)`.

#### Scenario: collect_transfer_data gathers all four sections
- **WHEN** `collect_transfer_data(root)` is called after SSR rendering
- **THEN** the returned `TransferPayload` SHALL have `fetches`, `async_results`, `signals`, and `resources` populated

#### Scenario: collect_transfer_data handles components with no signals
- **WHEN** a component has no `__signal_members__` entries
- **THEN** that component's transfer id SHALL not appear in the `signals` dict (or shall map to an empty dict)

#### Scenario: Two instances of the same component produce distinct entries
- **WHEN** the rendered tree contains two instances of one component with transferable state
- **THEN** the `signals` (or `async_results`) section SHALL contain one entry per instance, keyed by distinct transfer ids

### Requirement: serialize_payload and deserialize_payload shall support compressed payloads

`serialize_payload()` SHALL accept an optional `compression_threshold: int | None` parameter. When the serialized payload exceeds the threshold, it SHALL be gzip-compressed via `zlib`, base64-encoded, and wrapped in a `{"__webcompy_compressed__": true, ...}` envelope. `deserialize_payload()` SHALL detect the `__webcompy_compressed__` flag and decompress accordingly. Uncompressed payloads (without the flag) SHALL be processed as before, ensuring backward compatibility.

#### Scenario: Round-trip compressed payload
- **WHEN** a `TransferPayload` is serialized with compression enabled
- **AND** the serialized size exceeds the threshold
- **AND** the compressed output is passed to `deserialize_payload()`
- **THEN** the resulting `TransferPayload` SHALL be equal to the original (all fields preserved)

#### Scenario: Uncompressed payload backward compatibility
- **WHEN** `deserialize_payload()` receives a payload without `__webcompy_compressed__`
- **THEN** the payload SHALL be processed as uncompressed JSON
- **AND** the behavior SHALL be identical to the pre-compression implementation

### Requirement: RESOURCE_DATA_KEY shall expose embedded resource bytes to the browser port

`webcompy/di/_keys.py` SHALL define `RESOURCE_DATA_KEY = InjectKey[dict[str, str]]("webcompy-resource-data")` (mirroring the existing `HYDRATION_DATA_KEY` and `HYDRATION_SIGNAL_DATA_KEY` pattern). The value SHALL be the decoded `payload.resources` dict (base64 strings keyed by package-relative path).

#### Scenario: RESOURCE_DATA_KEY importable
- **WHEN** a developer writes `from webcompy.di import RESOURCE_DATA_KEY`
- **THEN** the import SHALL succeed
- **AND** the key SHALL be usable as the first argument to `inject()`

#### Scenario: Browser port consumes RESOURCE_DATA_KEY during hydration
- **WHEN** `BrowserResourcePort().load_text("templates/card.html")` is called and `RESOURCE_DATA_KEY` is provided in the DI scope with a matching entry
- **THEN** the base64-decoded content SHALL be returned
- **AND** no HTTP fetch SHALL be issued

### Requirement: SSR shall populate payload.resources from ServerResourcePort

During SSR/SSG, after component rendering completes for a request, `ServerRenderContext` SHALL collect the recorded resources from the current render context's `ServerResourcePort` (via `port.get_recorded_resources()`) and populate `TransferPayload.resources` with the path → bytes mapping. Recorded resources SHALL be scoped to the render context: resources loaded while generating other pages or serving other requests SHALL NOT appear. The codec pipeline SHALL base64-encode the bytes prior to JSON serialization.

#### Scenario: Loaded resource appears in hydration payload
- **WHEN** an async component in an SSR'd page calls `await load_text("templates/card.html")`
- **AND** the resource file exists
- **THEN** the resulting `__webcompy_data__` script SHALL include `"templates/card.html"` in the `resources` dict
- **AND** the value SHALL be the base64 of the file's bytes

#### Scenario: Failed load does not appear in payload
- **WHEN** a component calls `await load_text("missing.html")` and the load raises
- **THEN** the `resources` dict SHALL NOT contain `"missing.html"` after SSR

#### Scenario: Same resource loaded twice appears once in payload
- **WHEN** two components call `await load_text("templates/card.html")` during the same SSR pass
- **THEN** the `resources` dict SHALL contain a single entry for `"templates/card.html"` with the latest content

#### Scenario: Previously generated page's resources do not leak
- **WHEN** SSG generates page A (loading `documents/a.md`) and then page B (loading `documents/b.md`)
- **THEN** page B's payload `resources` SHALL contain `"documents/b.md"` but NOT `"documents/a.md"` (in the default per-context transfer mode)
- **AND** page A's payload SHALL contain `"documents/a.md"` only

### Requirement: SSG SHALL support an opt-in full text-resource transfer mode

Static site generation SHALL support an opt-in mode in which every allow-listed text resource is embedded in every generated page's transfer payload, regardless of which resources the page itself loaded. In this mode, client-side navigation SHALL NOT issue resource fetches for allow-listed text resources, because the browser port resolves them from the payload. Text resources SHALL be identified by a framework-fixed extension allowlist (`.md`, `.markdown`, `.txt`, `.json`, `.csv`, `.yaml`, `.yml`, `.toml`, `.svg`, `.html`, `.xml`), and binary resources SHALL be excluded. The transfer mode SHALL be configurable via the build configuration; the text-resource classification is fixed by the framework and may be extended in future framework versions. The default mode SHALL remain per-context ("used") transfer.

#### Scenario: Full text-resource transfer enabled
- **WHEN** SSG runs with the full text-resource transfer mode enabled
- **AND** the resource allow-list contains `documents/a.md` through `documents/z.md`
- **THEN** every generated page's payload SHALL contain all of those markdown resources
- **AND** the output SHALL be identical regardless of route generation order

#### Scenario: Navigation issues no resource fetch in full-transfer mode
- **WHEN** a user lands on any generated page of a site built with the full text-resource transfer mode
- **AND** navigates client-side to another page whose component loads an allow-listed text resource
- **THEN** the resource SHALL resolve from the transferred payload or browser cache
- **AND** no request to the resource endpoint SHALL be issued

#### Scenario: Binary resources are excluded from full transfer
- **WHEN** the resource allow-list contains `assets/logo.png`
- **AND** the full text-resource transfer mode is enabled
- **THEN** generated payloads SHALL NOT contain `assets/logo.png`

### Requirement: Payload compression shall apply to the resources field

The existing `compression_threshold` mechanism (gzip envelope triggered above the size threshold, via the `__webcompy_compressed__` flag) SHALL apply to v3 payloads including the new `resources` field. No special-case compression logic SHALL be added for `resources` specifically.

#### Scenario: Large resources trigger compression
- **WHEN** the unencoded payload size exceeds the configured `compression_threshold`
- **THEN** the serialized output SHALL be gzipped and base64-encoded with the `__webcompy_compressed__` envelope
- **AND** the `resources` field SHALL be included in the gzipped output

## Limitations

Only `Signal`, `ReactiveList`, and `ReactiveDict` values created via the `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composables are transferred. Signals created outside these composables (e.g., `count = Signal(0)` directly, or `use_async_result` internal state) are NOT captured for transfer. The composables register created signals in `Context._transferable_signals`, which `Component.__setup()` merges into `__signal_members__` for collection by `collect_transfer_data()`.

Restored values bypass `set_value()` so downstream reactive notifications do not fire — the transferred values represent a coherent SSR snapshot that is rebuilt deterministically on the browser.
