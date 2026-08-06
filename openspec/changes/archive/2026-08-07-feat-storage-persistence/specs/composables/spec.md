# Delta: composables

## ADDED Requirements

### Requirement: Storage persistence composables shall provide reactive localStorage/sessionStorage-backed state

The framework SHALL provide `use_local_storage(key, default)` and `use_session_storage(key, default)` composables, importable from `webcompy` top-level and from `webcompy.storage`, each returning a `Reactive[T]`. `default` SHALL accept either a value or a zero-argument factory callable.

In the browser (PyScript) environment, the composable SHALL read the current stored value for `key` at creation time and use it as the signal's initial value; when the key is absent, the default SHALL be used. Every subsequent update of the returned signal SHALL be automatically written back to the corresponding Web Storage API. Values SHALL be encoded with `json.dumps` and decoded with `json.loads`.

In any non-PyScript environment (SSR, SSG, server-side tests), the composable SHALL NOT access any storage API and SHALL return `Reactive(default)`.

#### Scenario: Read persisted value on creation
- **GIVEN** the browser's `localStorage` contains `{"theme": "\"dark\""}`-style JSON under key `"theme"`
- **WHEN** a component setup calls `use_local_storage("theme", "light")`
- **THEN** the returned signal's value SHALL be `"dark"`

#### Scenario: Default when key absent
- **WHEN** a component setup calls `use_local_storage("missing", lambda: 42)` and the key is absent
- **THEN** the returned signal's value SHALL be `42`

#### Scenario: Automatic write-back on update
- **GIVEN** `theme = use_local_storage("theme", "light")` in the browser
- **WHEN** `theme.value = "dark"` is assigned
- **THEN** `localStorage.getItem("theme")` SHALL return `'"dark"'`

#### Scenario: SSR performs no storage access
- **WHEN** `use_local_storage("theme", "light")` is called during SSR/SSG (non-PyScript environment)
- **THEN** the returned signal's value SHALL be `"light"`
- **AND** no browser storage API SHALL be accessed

#### Scenario: Callable outside component setup
- **WHEN** `use_local_storage("k", 0)` is called outside any component setup function
- **THEN** a working `Reactive` SHALL be returned
- **AND** no `UserWarning` SHALL be emitted

#### Scenario: Storage-backed signals are excluded from SSR transfer
- **WHEN** a component uses `use_local_storage` inside setup during SSR
- **THEN** the signal SHALL NOT be registered in the SSR transfer payload

### Requirement: Storage composables shall degrade gracefully on failure

Storage composables SHALL follow a non-fatal failure policy: a corrupted stored value (invalid JSON) SHALL produce a `logging.warning` and fall back to the default; a non-JSON-serializable value on write SHALL produce a warning and skip the write; a `setItem` failure (quota, privacy mode) SHALL be caught, logged, and swallowed. No storage failure SHALL break signal reactivity or propagate to the caller.

#### Scenario: Corrupted stored value
- **GIVEN** `localStorage` contains invalid JSON under key `"settings"`
- **WHEN** `use_local_storage("settings", lambda: {})` is called in the browser
- **THEN** a warning SHALL be logged
- **AND** the signal's value SHALL be `{}`

#### Scenario: Non-serializable value skips write
- **GIVEN** `data = use_local_storage("data", None)` in the browser
- **WHEN** `data.value = object()` is assigned
- **THEN** a warning SHALL be logged
- **AND** the write SHALL be skipped
- **AND** the signal's in-memory value SHALL update normally
