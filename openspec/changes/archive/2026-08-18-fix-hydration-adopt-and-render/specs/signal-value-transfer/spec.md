# signal-value-transfer — Environment-Stable Auto Keys Deltas

## MODIFIED Requirements

### Requirement: Signal values shall be restored on the browser after component setup

During browser hydration, the `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composables SHALL check `HYDRATION_SIGNAL_DATA_KEY` (via `inject()`) during component setup, before the factory is invoked. For each composable call:

1. The framework SHALL compute `component_id = generate_id(context._component_name)`.
2. If `payload[component_id][key]` exists, the factory SHALL be **skipped** and the signal SHALL be created directly with the restored value: `Signal(restored_value)` (or `ReactiveList(restored_value)` / `ReactiveDict(restored_value)` for collection composables).
3. If the key is not found (server-side, client-side navigation, or non-transferable context), the factory SHALL run: `Signal(factory())` (or corresponding constructor for collection types).

The restored value SHALL be the post-codec-decode Python object (deserialize_payload already applies `decode()`). No additional decoding is needed in composables.

The `_restore_signals()` method SHALL be **removed** from `Component._render()`. Restoration is fully handled by the factory-skip mechanism during setup.

Auto transfer keys SHALL be stable across the SSR environment and the browser environment: the key SHALL be derived from the call site's module identity and position (module name, line, and column), NOT from the module's absolute filesystem path, which differs between the SSR checkout and the browser wheel bundle. Different call sites within the same module SHALL produce distinct keys; the same call site SHALL produce the same key in both environments. The key SHALL NOT contain an absolute filesystem path. Module-identity keys assume the call site lives in a package module with a stable dotted name: for a script executed as `__main__`, the module name differs between the SSR checkout and the browser wheel bundle, so transfer restoration is not guaranteed for single-file apps (package-structured apps are the supported deployment for transferable composables).

#### Scenario: Factory skip eliminates flash
- **WHEN** a component setup calls `count = use_state(lambda: 0)` (default 0)
- **AND** the transfer payload contains a value for this signal's key
- **THEN** the factory SHALL be skipped
- **AND** the `Signal` SHALL be created with the restored value
- **AND** the first render SHALL read the restored value (no flash of default)

#### Scenario: Factory runs on server
- **WHEN** `use_state(lambda: read_cookie("theme"))` is called during SSR
- **AND** `HYDRATION_SIGNAL_DATA_KEY` is not provided (server context)
- **THEN** the factory SHALL run, reading the cookie
- **AND** the resulting `Signal` SHALL hold the cookie value

#### Scenario: Factory runs on browser client-side navigation
- **WHEN** `use_state(lambda: read_cookie("theme"))` is called during client-side navigation (no hydration payload for this component)
- **THEN** the factory SHALL run
- **AND** the resulting `Signal` SHALL hold the browser-computed value

#### Scenario: Restoring a signal whose auto key matches across environments
- **WHEN** a component setup called `count = use_state(lambda: 0)` during SSR with the call site in module `mypkg.components.counter`
- **AND** the browser loads the same component from the wheel bundle where the same call site lives in module `mypkg.components.counter` (different filesystem path)
- **AND** the transfer payload contains a value for this signal's key
- **THEN** the factory SHALL be skipped and the signal SHALL be created with the restored value

#### Scenario: Auto key does not embed the filesystem path
- **WHEN** an auto transfer key is generated for a `use_state()` call site
- **THEN** the key SHALL be based on the call site's module name (and line/column position), which is identical across environments
- **AND** the key SHALL NOT contain the absolute filesystem path of the source file

#### Scenario: Two call sites on the same line produce distinct keys
- **WHEN** a setup function calls `use_state()` twice on the same source line
- **THEN** the two signals SHALL receive distinct transfer keys
- **AND** both values SHALL be transferred and restored independently

#### Scenario: ReactiveList factory skip
- **WHEN** a component setup calls `items = use_reactive_list(lambda: [])` (default empty list)
- **AND** the transfer payload contains `{"<key>": [1, 2, 3]}` for this component
- **THEN** the factory SHALL be skipped
- **AND** a `ReactiveList` SHALL be created with `[1, 2, 3]`
- **AND** mutation methods (`append`, `pop`, etc.) SHALL work normally on the restored instance

#### Scenario: Restoration does not trigger notifications
- **WHEN** a Signal is created with a restored value via `Signal(restored)`
- **THEN** no `on_before_updating` / `on_after_updating` callbacks SHALL fire
- **AND** no downstream `Computed` signals SHALL recompute
- **AND** no `CallbackConsumerNode` instances SHALL be triggered

#### Scenario: Composable outside component context degrades gracefully
- **WHEN** `use_state(factory)` is called outside a component setup function (`_active_component_context` is `None`)
- **THEN** the factory SHALL always run (no payload check)
- **AND** the `Signal` SHALL be created without transfer registration
- **AND** a `UserWarning` SHALL be emitted ("use_state() called outside component setup; signal will not be transferred")
- **AND** no error SHALL be raised

#### Scenario: use_state() MUST NOT be called from on_after_rendering hooks
- **WHEN** `use_state(factory)` is called inside `@on_after_rendering` (or any post-setup hook) instead of the setup function
- **THEN** the `_active_component_context` SHALL be `None`
- **AND** the composable SHALL emit a `UserWarning` and return a non-transferable `Signal`
- **AND** this scenario documents the intended usage: `use_state()` and related composables SHALL be called from the component setup function (synchronously or inside an `await` of an async setup), not from lifecycle hooks
