## ADDED Requirements

### Requirement: Components shall restore Signal values after setup during hydration

During browser hydration, `Component._render()` SHALL call signal value restoration after `__init_component()` / `__setup()` completes and before template evaluation. The restoration SHALL read `payload.signals[component_id]` from the transfer payload (provided via `HYDRATION_DATA_KEY` DI) and restore each `(attr_name, encoded_value)` pair by decoding the value via `decode()` from `webcompy.hydration._codec` and setting `component.__signal_members__[attr_name]._value = decoded_value` directly (bypassing `set_value()`).

#### Scenario: Component restores Signal values before first render
- **WHEN** a component is hydrated in the browser
- **AND** the transfer payload contains Signal values for the component's ID
- **THEN** after `__setup()` creates Signals with default values
- **AND** before template evaluation reads Signal values
- **AND** each Signal's `_value` SHALL be overwritten with the decoded transfer value

#### Scenario: Component without transfer data renders with defaults
- **WHEN** a component is hydrated
- **AND** the transfer payload does not contain an entry for the component's ID
- **THEN** Signals SHALL retain their default values from setup
- **AND** no restoration SHALL occur

#### Scenario: Signals first created in on_before_rendering are not restored on initial hydration
- **WHEN** a component creates a Signal inside an `on_before_rendering` hook (not in `__setup__()`)
- **AND** the transfer payload contains a value for that Signal's attribute name
- **THEN** on the initial hydration cycle, restoration SHALL run before `on_before_rendering`, so the Signal does not yet exist in `__signal_members__`
- **AND** the restoration for that attribute name SHALL be skipped (best-effort, no error)
- **AND** the hook SHALL execute with the Signal at its default value
- **AND** on subsequent navigation-based hydration cycles, the Signal SHALL exist and its transferred value SHALL be restored
- **AND** developers who need server-computed values available in hooks SHOULD create the Signal in `__setup()` instead
