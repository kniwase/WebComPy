# Delta: components

## ADDED Requirements

### Requirement: Components shall support an on_error_captured setup hook

Component setup SHALL support registering error-capture hooks via `context.on_error_captured(fn)` (following the same active-component-context pattern as `on_before_destroy`). `fn` receives the raised `Exception` and MAY return `False` to mark the error handled and stop propagation. Hooks SHALL be invoked nearest-first when a descendant raises (see the `error-handling` capability for the full propagation order). Hooks SHALL be released when the component is destroyed. Calling the registration function outside component setup SHALL raise `LookupError`.

#### Scenario: Registration during setup
- **WHEN** a component setup calls `context.on_error_captured(lambda err: False)` and a descendant later raises
- **THEN** the hook SHALL be invoked with the exception before any boundary engages
- **AND** returning `False` SHALL prevent boundary engagement

#### Scenario: Registration outside setup raises
- **WHEN** `on_error_captured` registration is attempted outside a component setup function
- **THEN** a `LookupError` SHALL be raised

#### Scenario: Hooks released on destroy
- **WHEN** a component with captured-error hooks is destroyed
- **THEN** its hooks SHALL no longer be invoked for subsequent errors
