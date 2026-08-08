# Delta: composables

## ADDED Requirements

### Requirement: use_local_storage shall support opt-in cross-tab synchronization

`use_local_storage` SHALL accept a keyword-only `sync_tabs: bool = False` parameter. When `sync_tabs=True` in the PyScript environment, the returned signal SHALL subscribe to `storage` events from other tabs of the same origin: when another tab writes the subscribed key, the signal SHALL update to the incoming JSON-decoded value with normal reactivity (consumers notified); when another tab removes the key (`removeItem`, or `clear()` covering it), the signal SHALL reset to its default (re-invoking a factory default). Applying a remote value SHALL NOT trigger the automatic storage write-back, so receiving an event never re-broadcasts. Events for keys with no subscriber SHALL be ignored. A remote payload that fails JSON decoding SHALL log a warning and reset to the default. Concurrent writes from two tabs follow the platform's last-writer-wins event order; no merging is performed. Delivery of a value equal to the signal's current value is a no-op (no notification), consistent with the signal equality contract.

When `sync_tabs=False` (default), behavior SHALL be identical to before. On non-PyScript environments `sync_tabs=True` SHALL be a no-op (no listener is created; the default is rendered). `use_session_storage` SHALL NOT gain this capability.

Event listeners and proxies SHALL follow the framework's browser-resource lifecycle (`create_proxy` paired with `removeEventListener` and `destroy`), and listener registration SHALL use a single shared listener per app with key-based dispatch rather than one listener per signal instance.

#### Scenario: Remote write updates the signal
- **GIVEN** tab A and tab B both created `theme = use_local_storage("theme", "light", sync_tabs=True)`
- **WHEN** tab B sets `theme.value = "dark"`
- **THEN** tab A's `theme` signal SHALL become `"dark"`
- **AND** tab A's templates consuming `theme` SHALL re-render

#### Scenario: No re-broadcast from the receiving tab
- **GIVEN** tab A receives a remote update for key `"theme"`
- **THEN** tab A SHALL NOT write `"theme"` back to `localStorage` as part of applying the remote value

#### Scenario: Remote removal resets to default
- **GIVEN** `settings = use_local_storage("settings", lambda: {}, sync_tabs=True)` in tab A
- **WHEN** tab B removes the `"settings"` key
- **THEN** tab A's `settings` signal SHALL reset to `{}`

#### Scenario: Default preserves current behavior
- **WHEN** `use_local_storage("theme", "light")` is called without `sync_tabs`
- **THEN** no `storage` event listener SHALL be registered for that instance

#### Scenario: Server-side no-op
- **WHEN** `use_local_storage("theme", "light", sync_tabs=True)` is called during SSR/SSG
- **THEN** no listener SHALL be created and the default SHALL be rendered

#### Scenario: Corrupted remote payload
- **WHEN** another tab stores invalid JSON under the subscribed key
- **THEN** a warning SHALL be logged
- **AND** the signal SHALL reset to its default

#### Scenario: Remote clear resets all synced keys
- **GIVEN** tab A subscribed to keys `"theme"` and `"settings"` with `sync_tabs=True`
- **WHEN** tab B calls `localStorage.clear()`
- **THEN** tab A's `"theme"` and `"settings"` signals SHALL each reset to their defaults

#### Scenario: Event for an unregistered key is ignored
- **GIVEN** tab A subscribed only to key `"theme"`
- **WHEN** tab B writes key `"other"`
- **THEN** tab A's `"theme"` signal SHALL remain unchanged

#### Scenario: No active app DI scope
- **WHEN** `use_local_storage("theme", "light", sync_tabs=True)` is called outside any app DI scope in a PyScript environment
- **THEN** a warning SHALL be logged
- **AND** no `storage` event listener SHALL be registered
- **AND** the signal SHALL behave like a normal non-syncing signal
