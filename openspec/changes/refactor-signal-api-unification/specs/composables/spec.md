## MODIFIED Requirements

### Requirement: Signal() direct construction shall emit DeprecationWarning

`Signal.__init__()` SHALL emit a `DeprecationWarning` (escalated from `UserWarning` in `feat-signal-composable`) with the message "Signal() is deprecated. Use signal(factory) instead." The `Signal` class SHALL remain as the return type of `signal()` and for type annotations.

The internal `Signal._create()` classmethod SHALL continue to bypass the warning for framework internal use.

#### Scenario: DeprecationWarning on direct construction
- **WHEN** user code calls `Signal(0)` directly
- **THEN** a `DeprecationWarning` SHALL be emitted (not `UserWarning`)
- **AND** the `Signal` SHALL still be created and function normally

#### Scenario: No warning from signal() composable
- **WHEN** `signal(lambda: 0)` creates a `Signal` internally
- **THEN** no `DeprecationWarning` SHALL be emitted
- **AND** `Signal._create()` SHALL be used instead of `Signal()`
