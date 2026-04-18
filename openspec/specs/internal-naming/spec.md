## Purpose

Internal identifier names should use correct English spelling. This spec documents the correct spelling of internal (private/dunder) API identifiers that were previously misspelled.

## Requirements

### Requirement: Internal identifiers use correct English spelling

All internal (private/dunder) API identifiers SHALL use the correct English spelling of their intended names.

#### Scenario: Signal event decorator uses correct spelling
- **WHEN** a signal class method is decorated with the event decorator
- **THEN** the decorator SHALL be named `_get_event` (not `_get_evnet`)

#### Scenario: Component definition attribute uses correct spelling
- **WHEN** a function is identified as a component definition
- **THEN** the marker attribute SHALL be named `__webcompy_component_definition__` (not `__webcompy_componet_definition__`)

#### Scenario: Component store uses correct spelling
- **WHEN** component generators are stored in the component store
- **THEN** the internal storage SHALL use the attribute name `__components` (not `__conponents`) and the generator parameter SHALL be named `component_generator` (not `componet_generator`)