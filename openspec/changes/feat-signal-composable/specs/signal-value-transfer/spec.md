## MODIFIED Requirements

### Requirement: Signal values shall be collected from __signal_members__ during SSR

During SSR/SSG, after the render tree completes and `await_pending()` finishes, the framework SHALL traverse the component tree and collect Signal values from each `Component`'s `__signal_members__` registry. For each `(attr_name, signal)` pair, the Signal's `_value` SHALL be encoded via `encode()` from `webcompy.hydration._codec` and stored in the payload as `signals[component_id][attr_name] = encoded_value`. Only `Signal`, `Computed`, `ReactiveList`, and `ReactiveDict` instances (subclasses of `SignalBase`) SHALL be collected.

> **BREAKING CHANGE**: Computed values are no longer collected for transfer. Only source Signals created via `use_state()` / `use_reactive_list()` / `use_reactive_dict()` are transferred. Previously (base spec), Computed cached values were included in the payload.

The `__signal_members__` registry SHALL be populated by the `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composables via `Context._transferable_signals` during component setup. The `Component.__setup()` method SHALL merge `context._transferable_signals` into `self.__signal_members__` after the setup function returns. For async components, the merge SHALL also occur after the async body resolves in `_render()` (per `fix-async-component-active-context`).

#### Scenario: Collecting Signal values created via use_state() composable
- **WHEN** `collect_transfer_data(root)` traverses a `Component` whose setup called `count = use_state(lambda: 5)`
- **THEN** the payload's `signals` section SHALL contain `{component_id: {"<auto-key>": 5}}`

#### Scenario: Collecting Signal values with explicit key
- **WHEN** a component setup called `count = use_state("count", lambda: 5)`
- **THEN** the payload's `signals` section SHALL contain `{component_id: {"count": 5}}`

#### Scenario: Collecting ReactiveList values created via use_reactive_list()
- **WHEN** a component setup called `items = use_reactive_list(lambda: [1, 2, 3])`
- **THEN** the payload's `signals` section SHALL include `{component_id: {"<key>": [1, 2, 3]}}`

#### Scenario: Collecting ReactiveDict values created via use_reactive_dict()
- **WHEN** a component setup called `settings = use_reactive_dict(lambda: {"theme": "dark"})`
- **THEN** the payload's `signals` section SHALL include `{component_id: {"<key>": {"theme": "dark"}}}`

#### Scenario: Collecting Computed cached values
- **WHEN** a component setup called `doubled = use_computed(lambda: count.value * 2)` where `count` was set to `5`
- **AND** the Computed has been evaluated during render (cached value is 10)
- **THEN** the payload's `signals` section SHALL NOT include the computed value (only transfer sources, not derivations)

#### Scenario: Non-serializable Signal value is dropped with warning
- **WHEN** a Signal holds a value that the codec cannot encode (e.g., a file handle)
- **AND** `collect_transfer_data(root)` processes it
- **THEN** the Signal SHALL be excluded from the payload
- **AND** a warning SHALL be logged

#### Scenario: Component with no composable calls
- **WHEN** a `Component` has no `use_state()`, `use_reactive_list()`, or `use_reactive_dict()` calls in its setup
- **THEN** the payload's `signals` section SHALL contain an empty dict `{}` for that component ID (or omit it entirely)

### Requirement: Signal values shall be restored on the browser after component setup

During browser hydration, the `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composables SHALL check `HYDRATION_SIGNAL_DATA_KEY` (via `inject()`) during component setup, before the factory is invoked. For each composable call:

1. The framework SHALL compute `component_id = generate_id(context._component_name)`.
2. If `payload[component_id][key]` exists, the factory SHALL be **skipped** and the signal SHALL be created directly with the restored value: `Signal._create(restored_value)` (or `ReactiveList._create(restored_value)` / `ReactiveDict._create(restored_value)` for collection composables).
3. If the key is not found (server-side, client-side navigation, or non-transferable context), the factory SHALL run: `Signal._create(factory())` (or corresponding `_create` for collection types).

The restored value SHALL be the post-codec-decode Python object (deserialize_payload already applies `decode()`). No additional decoding is needed in composables.

The `_restore_signals()` method SHALL be **removed** from `Component._render()`. Restoration is fully handled by the factory-skip mechanism during setup.

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

#### Scenario: ReactiveList factory skip
- **WHEN** a component setup calls `items = use_reactive_list(lambda: [])` (default empty list)
- **AND** the transfer payload contains `{"<key>": [1, 2, 3]}` for this component
- **THEN** the factory SHALL be skipped
- **AND** a `ReactiveList` SHALL be created with `[1, 2, 3]`
- **AND** mutation methods (`append`, `pop`, etc.) SHALL work normally on the restored instance

#### Scenario: Restoration does not trigger notifications
- **WHEN** a Signal is created with a restored value via `Signal._create(restored)`
- **THEN** no `on_before_updating` / `on_after_updating` callbacks SHALL fire
- **AND** no downstream `Computed` signals SHALL recompute
- **AND** no `CallbackConsumerNode` instances SHALL be triggered

#### Scenario: Composable outside component context degrades gracefully
- **WHEN** `use_state(factory)` is called outside a component setup function (`_active_component_context` is `None`)
- **THEN** the factory SHALL always run (no payload check)
- **AND** the `Signal` SHALL be created without transfer registration
- **AND** a `UserWarning` SHALL be emitted ("use_state() called outside component setup; signal will not be transferred")
- **AND** no error SHALL be raised

### Requirement: TransferPayload shall include a signals section at version 2

`TransferPayload` SHALL include a `signals: dict[str, dict[str, Any]]` field mapping component ID to a dict of `{key: encoded_value}`. The `__webcompy_transfer_version__` SHALL be `2` for payloads containing the `signals` section. The `deserialize_payload()` function SHALL accept both version 1 (no `signals` section) and version 2 (with `signals` section) payloads.

#### Scenario: Version 2 payload structure
- **WHEN** `serialize_payload()` produces a payload with Signal values
- **THEN** the JSON SHALL include `"__webcompy_transfer_version__": 2`
- **AND** a `"signals"` key SHALL be present

#### Scenario: Version 1 payload backward compatibility
- **WHEN** `deserialize_payload()` receives a version 1 JSON string (no `signals` key)
- **THEN** the `TransferPayload.signals` field SHALL default to an empty dict `{}`
- **AND** no Signal restoration SHALL occur
