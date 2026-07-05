# Signal Value Transfer

## Purpose

`AsyncResult` states and `FetchPort` response caches are already transferred from server to browser via the hydration data mechanism. However, application-level `Signal` values (the primary state primitive) are not. Components that derive UI state directly from `Signal` values experience a flash of default values during hydration — the browser re-initializes signals with their defaults and only converges to the correct state when user interaction or async data updates them.

This capability extends the hydration data transfer to include `Signal`, `Computed`, `ReactiveList`, and `ReactiveDict` values. The `SignalReceivable.__signal_members__` mechanism auto-tracks every Signal instance assigned to a component's `self` attributes, so no explicit registration is needed. Values are collected after SSR rendering completes, encoded via the codec engine, and restored on the browser after component setup, eliminating the flash of default values.

## Requirements

### Requirement: Signal values shall be collected from __signal_members__ during SSR

During SSR/SSG, after the render tree completes and `await_pending()` finishes, the framework SHALL traverse the component tree and collect Signal values from each `Component`'s `__signal_members__` registry. For each `(attr_name, signal)` pair, the Signal's `_value` SHALL be encoded via `encode()` from `webcompy.hydration._codec` and stored in the payload as `signals[component_id][attr_name] = encoded_value`. Only `Signal`, `Computed`, `ReactiveList`, and `ReactiveDict` instances (subclasses of `SignalBase`) SHALL be collected.

#### Scenario: Collecting Signal values from a component
- **WHEN** `collect_transfer_data(root)` traverses a `Component` with `self.count = Reactive(5)` and `self.name = Reactive("Alice")`
- **THEN** the payload's `signals` section SHALL contain `{component_id: {"count": 5, "name": "Alice"}}`

#### Scenario: Collecting Computed cached values
- **WHEN** a `Component` has `self.doubled = Computed(lambda: self.count * 2)` where `self.count = Reactive(5)`
- **AND** the Computed has been evaluated during render (cached value is 10)
- **THEN** the payload's `signals` section SHALL include `{"doubled": 10}` (the cached value)

#### Scenario: Collecting ReactiveList values
- **WHEN** a `Component` has `self.items = ReactiveList([1, 2, 3])`
- **THEN** the payload's `signals` section SHALL include `{"items": [1, 2, 3]}`

#### Scenario: Non-serializable Signal value is dropped with warning
- **WHEN** a Signal holds a value that the codec cannot encode (e.g., a file handle)
- **AND** `collect_transfer_data(root)` processes it
- **THEN** the Signal SHALL be excluded from the payload
- **AND** a warning SHALL be logged

#### Scenario: Component with no self-assigned Signals
- **WHEN** a `Component` has no Signal instances assigned to `self`
- **THEN** the payload's `signals` section SHALL contain an empty dict `{}` for that component ID (or omit it entirely)

### Requirement: Signal values shall be restored on the browser after component setup

During browser hydration, after component `__setup()` / `__init_component()` completes and before template evaluation, the framework SHALL restore Signal values from the transfer payload. For each `(attr_name, encoded_value)` in `payload.signals[component_id]`, the framework SHALL locate `component.__signal_members__[attr_name]`, decode the value via `decode()` from `webcompy.hydration._codec`, and set `signal._value = decoded_value` directly (bypassing `set_value()` to avoid triggering notifications).

#### Scenario: Restoring Signal values eliminates flash
- **WHEN** a component has `self.count = Reactive(0)` (default) during setup
- **AND** the transfer payload contains `{"count": 5}` for this component
- **THEN** after restoration, `self.count._value` SHALL be `5`
- **AND** the first render SHALL read `5` (no flash of `0`)

#### Scenario: Restoring Computed cached value
- **WHEN** a component has `self.doubled = Computed(...)` that evaluates to `0` during setup (default source)
- **AND** the transfer payload contains `{"doubled": 10}` for this component
- **THEN** after restoration, `self.doubled._value` SHALL be `10`
- **AND** no recompute SHALL be triggered
- **AND** the first render SHALL read `10`

#### Scenario: Restoration does not trigger notifications
- **WHEN** Signal values are restored via direct `_value` assignment
- **THEN** no `on_before_updating` / `on_after_updating` callbacks SHALL fire
- **AND** no downstream `Computed` signals SHALL recompute
- **AND** no `CallbackConsumerNode` instances SHALL be triggered

#### Scenario: Missing component ID in payload
- **WHEN** a component's ID is not present in `payload.signals`
- **THEN** no restoration SHALL occur for that component
- **AND** Signals SHALL retain their default values from setup

#### Scenario: Missing attr_name in __signal_members__
- **WHEN** the payload contains `{"count": 5}` for a component
- **AND** the component's `__signal_members__` does not contain `"count"` (e.g., component structure changed)
- **THEN** the restoration for `"count"` SHALL be skipped
- **AND** no error SHALL be raised (best-effort restoration)

### Requirement: Signal collection shall occur after await_pending and before ctx.dispose

On the server, `collect_transfer_data()` SHALL be called after `await scheduler.await_pending()` completes (so that async-resolved Signal values are settled) and before `ctx.dispose()` (so that the component tree and its Signal instances are still accessible).

#### Scenario: Collection timing in generate_html
- **WHEN** `generate_html()` runs the SSR pipeline
- **THEN** the call order SHALL be: `await ctx._root._render()` → `await scheduler.await_pending()` → `collect_transfer_data(root)` → `ctx.dispose()`

### Requirement: TransferPayload shall include a signals section at version 2

`TransferPayload` SHALL include a `signals: dict[str, dict[str, Any]]` field mapping component ID to a dict of `{attr_name: encoded_value}`. The `__webcompy_transfer_version__` SHALL be `2` for payloads containing the `signals` section. The `deserialize_payload()` function SHALL accept both version 1 (no `signals` section) and version 2 (with `signals` section) payloads.

#### Scenario: Version 2 payload structure
- **WHEN** `serialize_payload()` produces a payload with Signal values
- **THEN** the JSON SHALL include `"__webcompy_transfer_version__": 2`
- **AND** a `"signals"` key SHALL be present

#### Scenario: Version 1 payload backward compatibility
- **WHEN** `deserialize_payload()` receives a version 1 payload (no `signals` section)
- **THEN** the `TransferPayload.signals` field SHALL default to an empty dict `{}`
- **AND** no Signal restoration SHALL occur
