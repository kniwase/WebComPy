# Spec Delta

## ADDED Requirements

### Requirement: BrowserHistoryPort shall safely convert JavaScript history state to Python dicts

When reading `window.history.state` during `popstate` events (`_on_popstate`) or window state synchronization (`refresh_from_window`), `BrowserHistoryPort` SHALL convert non-null JavaScript proxy values to Python mappings via PyScript/Pyodide FFI conversion rather than invoking `.to_dict()`, and SHALL fall back to `None` when the state is null, undefined, or not a mapping.

#### Scenario: Popstate with non-null JSON history state

- **WHEN** the user triggers browser Back/Forward (`popstate`) onto an entry whose `window.history.state` is a JavaScript object created by `pushState`
- **THEN** `BrowserHistoryPort` SHALL extract the state as a Python `dict` without raising `AttributeError`
- **AND** the router SHALL navigate to the restored path cleanly

#### Scenario: Refreshing from window when history.state is non-dict

- **WHEN** `refresh_from_window()` runs and `window.history.state` is null or a non-object JS value
- **THEN** `BrowserHistoryPort` SHALL normalize state to `None` without raising an exception
