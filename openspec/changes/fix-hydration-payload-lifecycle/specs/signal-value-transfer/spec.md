## MODIFIED Requirements

### Requirement: Signal values shall be collected from __signal_members__ during SSR

During SSR/SSG, after the render tree completes and `await_pending()` finishes, the framework SHALL traverse the component tree and collect Signal values from each `Component`'s `__signal_members__` registry. For each `(attr_name, signal)` pair, the Signal's `_value` SHALL be encoded via `encode()` from `webcompy.hydration._codec` and stored in the payload as `signals[transfer_id][attr_name] = encoded_value`, where `transfer_id` is the component's per-instance transfer identity (see "Per-instance transfer identity"). Only `Signal`, `ReactiveList`, and `ReactiveDict` instances (subclasses of `SignalBase`) SHALL be collected.

The `__signal_members__` registry SHALL be populated by the `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composables via `Context._transferable_signals` during component setup. The `Component.__setup()` method SHALL merge `context._transferable_signals` into `self.__signal_members__` after the setup function returns. For async components, the merge SHALL also occur after the async body resolves in `_render()`.

Two instances of the same component in one rendered tree SHALL produce two distinct payload entries; collection SHALL NOT overwrite one instance's values with another's.

#### Scenario: Collecting Signal values created via use_state() composable
- **WHEN** `collect_transfer_data(root)` traverses a `Component` whose setup called `count = use_state(lambda: 5)`
- **THEN** the payload's `signals` section SHALL contain `{transfer_id: {"<auto-key>": 5}}` for that instance's transfer id

#### Scenario: Collecting Signal values with explicit key
- **WHEN** a component setup called `count = use_state("count", lambda: 5)`
- **THEN** the payload's `signals` section SHALL contain `{transfer_id: {"count": 5}}`

#### Scenario: Collecting ReactiveList values created via use_reactive_list()
- **WHEN** a component setup called `items = use_reactive_list(lambda: [1, 2, 3])`
- **THEN** the payload's `signals` section SHALL include `{transfer_id: {"<key>": [1, 2, 3]}}`

#### Scenario: Collecting ReactiveDict values created via use_reactive_dict()
- **WHEN** a component setup called `settings = use_reactive_dict(lambda: {"theme": "dark"})`
- **THEN** the payload's `signals` section SHALL include `{transfer_id: {"<key>": {"theme": "dark"}}}`

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
- **THEN** the payload's `signals` section SHALL contain an empty dict `{}` for that component's transfer id (or omit it entirely)

#### Scenario: Two instances of the same component are collected independently
- **WHEN** one rendered tree contains two instances of a component whose setup called `use_state("count", ...)`
- **THEN** the payload's `signals` section SHALL contain two entries with distinct transfer ids
- **AND** each entry SHALL hold its own instance's value

### Requirement: Signal values shall be restored on the browser after component setup

During the initial browser hydration window, the `use_state()`, `use_reactive_list()`, and `use_reactive_dict()` composables SHALL check `HYDRATION_SIGNAL_DATA_KEY` (via `inject()`) during component setup, before the factory is invoked. For each composable call:

1. The framework SHALL compute the component's per-instance transfer id (see "Per-instance transfer identity").
2. If `payload[transfer_id][key]` exists, the factory SHALL be **skipped** and the signal SHALL be created directly with the restored value: `Signal(restored_value)` (or `ReactiveList(restored_value)` / `ReactiveDict(restored_value)` for collection composables).
3. If the key is not found (server-side, client-side navigation, or non-transferable context), the factory SHALL run: `Signal(factory())` (or corresponding constructor for collection types).
4. The restored value SHALL be an **independent copy** of the payload value: mutating the restored `Signal` / `ReactiveList` / `ReactiveDict` value SHALL NOT mutate the hydration payload, and each restore from the same payload entry SHALL yield the original value.

Restoration SHALL only occur while the initial hydration window is open. The hydration window opens before the initial render pass creates or hydrates the component tree and closes when the initial render pass (including the render-task drain that gates the hydration reveal) completes, whether it succeeds or fails. Component setups that run after the window has closed — including client-side navigations and dynamically created components — SHALL NOT consult the transfer payload: the factory SHALL run even if the payload contains a matching entry.

The restored value SHALL be the post-codec-decode Python object (deserialize_payload already applies `decode()`). No additional decoding is needed in composables.

The `_restore_signals()` method SHALL be **removed** from `Component._render()`. Restoration is fully handled by the factory-skip mechanism during setup.

Auto transfer keys SHALL be stable across the SSR environment and the browser environment: the key SHALL be derived from the call site's module identity and position (module name, line, and column), NOT from the module's absolute filesystem path, which differs between the SSR checkout and the browser wheel bundle. Different call sites within the same module SHALL produce distinct keys; the same call site SHALL produce the same key in both environments. The key SHALL NOT contain an absolute filesystem path. Module-identity keys assume the call site lives in a package module with a stable dotted name: for a script executed as `__main__`, the module name differs between the SSR checkout and the browser wheel bundle, so transfer restoration is not guaranteed for single-file apps (package-structured apps are the supported deployment for transferable composables).

#### Scenario: Factory skip eliminates flash
- **WHEN** a component setup calls `count = use_state(lambda: 0)` (default 0)
- **AND** the transfer payload contains a value for this component instance's transfer id and signal key
- **AND** the setup runs during the initial hydration window
- **THEN** the factory SHALL be skipped
- **AND** the `Signal` SHALL be created with the restored value
- **AND** the first render SHALL read the restored value (no flash of default)

#### Scenario: Factory runs on server
- **WHEN** `use_state(lambda: read_cookie("theme"))` is called during SSR
- **AND** `HYDRATION_SIGNAL_DATA_KEY` is not provided (server context)
- **THEN** the factory SHALL run, reading the cookie
- **AND** the resulting `Signal` SHALL hold the cookie value

#### Scenario: Factory runs on browser client-side navigation
- **WHEN** `use_state(lambda: read_cookie("theme"))` is called during client-side navigation after the initial hydration window has closed
- **THEN** the factory SHALL run
- **AND** the resulting `Signal` SHALL hold the browser-computed value
- **AND** this SHALL hold even if the initial page's payload contains an entry for the same component name

#### Scenario: Restoring a signal whose auto key matches across environments
- **WHEN** a component setup called `count = use_state(lambda: 0)` during SSR with the call site in module `mypkg.components.counter`
- **AND** the browser loads the same component from the wheel bundle where the same call site lives in module `mypkg.components.counter` (different filesystem path)
- **AND** the transfer payload contains a value for this component instance's key
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
- **AND** the transfer payload contains `{"<key>": [1, 2, 3]}` for this component instance
- **THEN** the factory SHALL be skipped
- **AND** a `ReactiveList` SHALL be created with `[1, 2, 3]`
- **AND** mutation methods (`append`, `pop`, etc.) SHALL work normally on the restored instance

#### Scenario: Mutating a restored collection does not corrupt the payload
- **WHEN** a `ReactiveList` is restored from a payload entry containing `[1, 2]`
- **AND** `append(3)` is called on the restored instance
- **THEN** the payload entry SHALL still contain `[1, 2]`
- **AND** restoring from the same payload entry again SHALL yield a `ReactiveList` with `[1, 2]`

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

#### Scenario: Stale payload value from the initial page is not restored after navigation
- **WHEN** the initial page contained a component whose `use_state()` value was transferred
- **AND** the user navigates client-side to a route whose tree contains a new instance of the same component
- **THEN** the new instance's `use_state()` SHALL run its factory instead of restoring the initial page's value

## ADDED Requirements

### Requirement: Per-instance transfer identity

Each component instance SHALL be assigned a transfer id of the form `<generate_id(component_name)>#<ordinal>`, where `ordinal` is a per-render-context, per-component-name creation-order counter starting at `0`. The transfer id SHALL be assigned before the component's setup function runs, so composables can use it during setup. SSR collection and browser restoration SHALL both use the transfer id as the payload key, so the N-th instance of a component created during hydration restores the N-th instance's values collected during SSR. Both sides rely on matching creation order between SSR rendering and the initial browser hydration pass; trees whose creation order differs between server and browser (e.g., environment-conditional subtrees) are unsupported, consistent with DOM hydration adoption.

The transfer id SHALL be scoped to hydration transfer only: the existing `component_id` used for scoped-CSS attributes (`webcompy-cid-*`) and hydration diagnostics SHALL remain the definition-stable `generate_id(component_name)` without an ordinal.

When no render context is available (e.g., unit tests constructing components directly), the transfer id SHALL fall back to the bare `generate_id(component_name)` form.

#### Scenario: Two instances restore their own values
- **WHEN** SSR renders two instances of component `Counter` with `use_state("count", ...)` values 1 and 2 (in creation order)
- **AND** the browser hydrates the same tree
- **THEN** the first-created `Counter` instance SHALL restore `1`
- **AND** the second-created `Counter` instance SHALL restore `2`

#### Scenario: Transfer id does not leak into scoped CSS attributes
- **WHEN** a component with scoped styles is rendered
- **THEN** its DOM node SHALL carry the definition-stable `webcompy-cid-<md5(name)>` attribute without any ordinal suffix

#### Scenario: Fallback to bare component id without a render context
- **WHEN** a component is constructed in a unit test without an active render context
- **THEN** its transfer id SHALL be `generate_id(component_name)` (no ordinal suffix)
