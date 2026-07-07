## MODIFIED Requirements

### Requirement: Signal values shall be collected from __signal_members__ during SSR

During SSR/SSG, after the render tree completes and `await_pending()` finishes, the framework SHALL traverse the component tree and collect Signal values from each `Component`'s `__signal_members__` registry. For each `(attr_name, signal)` pair, the Signal's `_value` SHALL be encoded via `encode()` from `webcompy.hydration._codec` and stored in the payload as `signals[component_id][attr_name] = encoded_value`. Only `Signal`, `Computed`, `ReactiveList`, and `ReactiveDict` instances (subclasses of `SignalBase`) SHALL be collected.

The `__signal_members__` registry SHALL be populated by the `signal()` composable via `Context._transferable_signals` during component setup. The `Component.__setup()` method SHALL merge `context._transferable_signals` into `self.__signal_members__` after the setup function returns. For async components, the merge SHALL also occur after the async body resolves in `_render()` (per `fix-async-component-active-context`).

#### Scenario: Collecting Signal values created via signal() composable
- **WHEN** `collect_transfer_data(root)` traverses a `Component` whose setup called `count = signal(lambda: 5)`
- **THEN** the payload's `signals` section SHALL contain `{component_id: {"<auto-key>": 5}}`

#### Scenario: Collecting Signal values with explicit key
- **WHEN** a component setup called `count = signal("count", lambda: 5)`
- **THEN** the payload's `signals` section SHALL contain `{component_id: {"count": 5}}`

#### Scenario: Collecting Computed cached values
- **WHEN** a component setup called `doubled = signal(lambda: count.value * 2)` where `count` was set to `5`
- **AND** the factory has been evaluated during render
- **THEN** the payload's `signals` section SHALL include the computed value

#### Scenario: Non-serializable Signal value is dropped with warning
- **WHEN** a Signal holds a value that the codec cannot encode (e.g., a file handle)
- **AND** `collect_transfer_data(root)` processes it
- **THEN** the Signal SHALL be excluded from the payload
- **AND** a warning SHALL be logged

#### Scenario: Component with no signal() calls
- **WHEN** a `Component` has no `signal()` calls in its setup
- **THEN** the payload's `signals` section SHALL contain an empty dict `{}` for that component ID (or omit it entirely)

### Requirement: Signal values shall be restored on the browser via factory-skip during setup

During browser hydration, the `signal()` composable SHALL check `HYDRATION_SIGNAL_DATA_KEY` (via `inject()`) during component setup, before the factory is invoked. For each `signal(key, factory)` call:

1. The framework SHALL compute `component_id = generate_id(context._component_name)`.
2. If `payload[component_id][key]` exists, the factory SHALL be **skipped** and the `Signal` SHALL be created directly with the restored value: `Signal._create(restored_value)`.
3. If the key is not found (server-side, client-side navigation, or non-transferable context), the factory SHALL run: `Signal._create(factory())`.

The restored value SHALL be the post-codec-decode Python object (deserialize_payload already applies `decode()`). No additional decoding is needed in `signal()`.

The `_restore_signals()` method SHALL be **removed** from `Component._render()`. Restoration is fully handled by the factory-skip mechanism during setup.

#### Scenario: Factory skip eliminates flash
- **WHEN** a component setup calls `count = signal(lambda: 0)` (default 0)
- **AND** the transfer payload contains a value for this signal's key
- **THEN** the factory SHALL be skipped
- **AND** the `Signal` SHALL be created with the restored value
- **AND** the first render SHALL read the restored value (no flash of default)

#### Scenario: Factory runs on server
- **WHEN** `signal(lambda: read_cookie("theme"))` is called during SSR
- **AND** `HYDRATION_SIGNAL_DATA_KEY` is not provided (server context)
- **THEN** the factory SHALL run, reading the cookie
- **AND** the resulting `Signal` SHALL hold the cookie value

#### Scenario: Factory runs on browser client-side navigation
- **WHEN** `signal(lambda: read_cookie("theme"))` is called during client-side navigation (no hydration payload for this component)
- **THEN** the factory SHALL run
- **AND** the resulting `Signal` SHALL hold the browser-computed value

#### Scenario: Restoration does not trigger notifications
- **WHEN** a Signal is created with a restored value via `Signal._create(restored)`
- **THEN** no `on_before_updating` / `on_after_updating` callbacks SHALL fire
- **AND** no downstream `Computed` signals SHALL recompute
- **AND** no `CallbackConsumerNode` instances SHALL be triggered

#### Scenario: signal() outside component context degrades gracefully
- **WHEN** `signal(factory)` is called outside a component setup function (`_active_component_context` is `None`)
- **THEN** the factory SHALL always run (no payload check)
- **AND** the `Signal` SHALL be created without transfer registration
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
