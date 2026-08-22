## MODIFIED Requirements

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

### Requirement: app.run shall restore transfer data

`app.run()` SHALL, before the first render, locate the `<script type="application/json" id="__webcompy_data__">` element in the DOM, parse its content using `deserialize_payload()`, and if the payload is valid:
1. Call `browser_fetch_port.populate_from_transfer(payload.fetches)`
2. Provide `payload.async_results` via `HYDRATION_DATA_KEY` in the root DI scope
3. Provide `payload.signals` via `HYDRATION_SIGNAL_DATA_KEY` in the root DI scope
4. Provide `payload.resources` via `RESOURCE_DATA_KEY` in the root DI scope

The `HYDRATION_SIGNAL_DATA_KEY` and `RESOURCE_DATA_KEY` SHALL be provided **before** any component creation, so that `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composable calls during component setup can access the payload via `inject(HYDRATION_SIGNAL_DATA_KEY)`, and `BrowserResourcePort` can access embedded resources via `inject(RESOURCE_DATA_KEY)`.

The `HYDRATION_DATA_KEY` and `HYDRATION_SIGNAL_DATA_KEY` payloads SHALL be valid only during the initial hydration window: the window opens before the initial render pass creates or hydrates the component tree and closes when the initial render pass (including the render-task drain that gates the hydration reveal) completes, whether it succeeds or fails. Component setups running after the window closes SHALL NOT restore from these payloads. The fetch-port response cache (`populate_from_transfer`) and `RESOURCE_DATA_KEY` are URL- and path-keyed respectively and are NOT subject to this lifecycle; they remain available for the app's lifetime.

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
