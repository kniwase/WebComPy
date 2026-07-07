## ADDED Requirements

### Requirement: Module-level signal() calls shall register in a global registry

When `signal()` is called outside a component setup context (`_active_component_context` is `None`), it SHALL register the created `Signal` in a module-level global registry (`_global_transferable_signals: dict[str, SignalBase]`). The registry SHALL use the same key generation logic (explicit key or auto-generated `file:line:column`) as component-level `signal()` calls.

If the factory fails at module import time (e.g., DI not initialized on browser), `signal()` SHALL catch the exception, create a `Signal(None)` placeholder, and register it. The exception SHALL be logged as a warning, not re-raised.

#### Scenario: Module-level signal registers in global registry
- **WHEN** `signal(lambda: 42)` is called at module level (no active component context)
- **THEN** the `Signal` SHALL be registered in `_global_transferable_signals`
- **AND** the factory SHALL run (producing 42 on the server, or failing on the browser)

#### Scenario: Module-level factory failure on browser
- **WHEN** `signal(lambda: inject(SOME_KEY).get("value"))` is called at module level on the browser
- **AND** `SOME_KEY` is not available in DI at import time
- **THEN** the factory SHALL raise an exception
- **AND** `signal()` SHALL catch the exception, create `Signal(None)`, and register it
- **AND** a warning SHALL be logged
- **AND** the module import SHALL NOT crash

### Requirement: collect_transfer_data shall collect global registry signals

`collect_transfer_data()` SHALL, in addition to walking the component tree for `__signal_members__`, walk `_global_transferable_signals` and collect their values. Global signals SHALL be stored in the payload under a reserved component ID `"__global__"`.

#### Scenario: Global signals collected during SSR
- **WHEN** `collect_transfer_data(root)` runs during SSR
- **AND** `_global_transferable_signals` contains entries
- **THEN** the payload's `signals` section SHALL include `{"__global__": {key: value, ...}}`

#### Scenario: No global signals
- **WHEN** `_global_transferable_signals` is empty
- **THEN** the `"__global__"` key SHALL be absent from the payload (or map to an empty dict)

### Requirement: app.run shall restore global signals after payload deserialization

`app.run()` SHALL, after deserializing the payload and before the first render, walk `_global_transferable_signals` and overwrite `signal._value` for any signal whose key is in `payload["__global__"]`. The overwrite SHALL use direct `_value` assignment (bypassing `set_value()`) to avoid triggering notifications (no subscribers exist at this point).

Signals whose keys are NOT in the payload SHALL retain their factory-produced values (which may be `None` if the factory failed at import time).

#### Scenario: Global signals restored before first render
- **WHEN** `app.run()` has deserialized the payload
- **AND** `_global_transferable_signals` contains signals
- **AND** the payload contains `{"__global__": {key: value}}`
- **THEN** each matching signal's `_value` SHALL be set to the transferred value
- **AND** non-matching signals SHALL retain their current values
- **AND** the restoration SHALL occur before any component rendering

#### Scenario: No global signals in payload
- **WHEN** the payload does not contain a `"__global__"` key
- **THEN** no global signal restoration SHALL occur
- **AND** global signals SHALL retain their factory-produced values
