## ADDED Requirements

### Requirement: CustomElementPort ABC shall exist in the port hierarchy

The framework SHALL provide a `CustomElementPort` abstract base class in `webcompy.ports` for custom-element registry and per-node binding operations. It SHALL define methods for ensuring a custom element is defined and for binding a DOM node to lifecycle and attribute callbacks. The port SHALL NOT import `Component`; component-specific callbacks SHALL be supplied as callables when binding.

#### Scenario: CustomElementPort is importable
- **WHEN** a developer imports `webcompy.ports`
- **THEN** `CustomElementPort` SHALL be accessible

#### Scenario: CustomElementPort cannot be instantiated directly
- **WHEN** a developer attempts to instantiate `CustomElementPort` directly
- **THEN** Python SHALL raise `TypeError` due to abstract methods

#### Scenario: Browser implementation creates native custom elements
- **WHEN** the browser `CustomElementPort` ensures a named element is defined
- **THEN** it SHALL register an `HTMLElement` subclass through `customElements.define` (or reuse a compatible existing definition)
- **AND** binding a node SHALL forward lifecycle and observed-attribute reactions to the supplied callbacks

#### Scenario: Port does not depend on the component module
- **WHEN** the custom-element port module is imported
- **THEN** it SHALL not import `webcompy.components._component` or any component class

### Requirement: CustomElementPort shall expose registry conflict behavior

When a custom element name is already defined, the browser `CustomElementPort` SHALL reuse the existing definition only when its WebComPy marker and observed-attribute metadata match. A non-WebComPy definition or an incompatible WebComPy definition SHALL raise `WebComPyComponentException` and SHALL not be replaced.

#### Scenario: Reusing a compatible definition
- **WHEN** two WebComPy definitions request the same custom element name with matching metadata
- **THEN** the second request SHALL reuse the existing browser definition
- **AND** no `customElements.define` call SHALL be issued for the duplicate

#### Scenario: Rejecting an incompatible definition
- **WHEN** a custom element name is already defined by another library or with different observed attributes
- **THEN** `WebComPyComponentException` SHALL be raised
- **AND** the existing browser definition SHALL remain unchanged
