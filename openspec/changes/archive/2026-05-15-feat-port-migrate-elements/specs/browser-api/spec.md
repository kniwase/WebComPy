## MODIFIED Requirements

### Requirement: Element system accesses DOMPort
The elements package SHALL obtain DOM port references through `inject(DOM_PORT_KEY)` from the DI system rather than importing `browser` directly. All existing `if browser:` guards SHALL be replaced with equivalent `if ENVIRONMENT == "pyscript":` checks.

#### Scenario: Element creates DOM element via port
- **WHEN** `ElementBase._create_node()` needs to create a DOM element
- **THEN** it SHALL call `inject(DOM_PORT_KEY).create_element(self._tag_name)` when `ENVIRONMENT == "pyscript"`
- **AND** raise `WebComPyException` otherwise

#### Scenario: Event handler creates proxy via FFIPort
- **WHEN** `_generate_event_handler()` creates an event handler
- **THEN** it SHALL call `inject(FFI_PORT_KEY).create_proxy(handler)` when `ENVIRONMENT == "pyscript"`
- **AND** return the raw Python handler otherwise

#### Scenario: SwitchElement schedules macro task via port
- **WHEN** `SwitchElement._refresh()` has deferred callbacks
- **THEN** it SHALL call `inject(DOM_PORT_KEY).schedule_macro_task(callback)` when `ENVIRONMENT == "pyscript"`

#### Scenario: RepeatElement uses ENVIRONMENT for runtime branching
- **WHEN** `RepeatElement._on_set_parent()` or `_update_dom_range()` runs
- **THEN** it SHALL use `ENVIRONMENT == "pyscript"` instead of `browser` truthiness checks
- **AND** behavior SHALL be identical to the pre-port implementation
