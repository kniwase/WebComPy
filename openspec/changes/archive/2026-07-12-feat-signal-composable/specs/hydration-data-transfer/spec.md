## MODIFIED Requirements

### Requirement: app.run shall restore transfer data

`app.run()` SHALL, before the first render, locate the `<script type="application/json" id="__webcompy_data__">` element in the DOM, parse its content using `deserialize_payload()`, and if the payload is valid:
1. Call `browser_fetch_port.populate_from_transfer(payload.fetches)`
2. Provide `payload.async_results` via `HYDRATION_DATA_KEY` in the root DI scope
3. Provide `payload.signals` via `HYDRATION_SIGNAL_DATA_KEY` in the root DI scope

The `HYDRATION_SIGNAL_DATA_KEY` SHALL be provided **before** any component creation, so that `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composable calls during component setup can access the payload via `inject(HYDRATION_SIGNAL_DATA_KEY)`.

If the payload is missing or invalid, the function SHALL proceed with an empty payload (all DI keys unprovided). The script element SHALL be removed from the DOM after reading.

#### Scenario: Valid payload is restored during app.run
- **WHEN** `app.run()` is called and the DOM contains a valid `__webcompy_data__` script tag
- **THEN** `BrowserFetchPort.populate_from_transfer()` SHALL be called with the `fetches` section
- **AND** `HYDRATION_DATA_KEY` SHALL be provided with the `async_results` section
- **AND** `HYDRATION_SIGNAL_DATA_KEY` SHALL be provided with the `signals` section
- **AND** both DI keys SHALL be available during component `__setup()`

#### Scenario: Missing payload proceeds with empty data
- **WHEN** `app.run()` is called and the DOM does not contain a `__webcompy_data__` script tag
- **THEN** the `BrowserFetchPort` cache SHALL be empty
- **AND** `HYDRATION_DATA_KEY` SHALL NOT be provided
- **AND** `HYDRATION_SIGNAL_DATA_KEY` SHALL NOT be provided
- **AND** components SHALL use the normal lifecycle (factories run, async functions execute)

#### Scenario: Script tag is removed after reading
- **WHEN** `app.run()` has read the `__webcompy_data__` script tag
- **THEN** the script tag SHALL be removed from the DOM

#### Scenario: Signal data available during setup
- **WHEN** a component's setup function calls `use_state(lambda: 0)`
- **AND** `HYDRATION_SIGNAL_DATA_KEY` was provided by `app.run()`
- **THEN** `inject(HYDRATION_SIGNAL_DATA_KEY)` SHALL return the signals payload
- **AND** `use_state()` SHALL check the payload for a matching key before running the factory
