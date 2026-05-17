## MODIFIED Requirements

### Requirement: Router receives HistoryPort via constructor
`Router` SHALL accept a `HistoryPort` instance as a constructor parameter rather than creating a `Location` internally.

#### Scenario: Router constructed with HistoryPort
- **WHEN** `Router(pages..., history=history_port)` is instantiated
- **THEN** `self._history` SHALL reference the provided `HistoryPort`
- **AND** `Router.__set_path__` SHALL delegate to `self._history.navigate()`

### Requirement: Location class removed
The `Location` class SHALL be removed. All path state and navigation functionality SHALL be provided by `HistoryPort`.

#### Scenario: HistoryPort replaces Location references
- **WHEN** code previously used `Location.__set_path__`
- **THEN** it SHALL use `HistoryPort.navigate()` instead

### Requirement: _browser/ directory removed
The `webcompy/_browser/` directory SHALL be fully deleted. All remaining `browser` references in Router files SHALL be migrated to `context.window.*` or port injection.

#### Scenario: _browser/ directory does not exist
- **WHEN** the framework is installed and imported
- **THEN** `webcompy/_browser/` SHALL not exist on disk

#### Scenario: Router files use context.window instead of browser
- **WHEN** Router files need window-level browser APIs
- **THEN** they SHALL access them via `pyscript.context.window` instead of the removed `browser` object

## REMOVED Requirements

### Requirement: Location popstate proxy
**Reason**: Replaced by `BrowserHistoryPort` which manages its own proxy lifecycle.
**Migration**: Use `BrowserHistoryPort` which handles popstate internally. No consumer-level cleanup needed.
