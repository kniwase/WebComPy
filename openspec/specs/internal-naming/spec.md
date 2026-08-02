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

### Requirement: Framework-internal methods invoked from coupled code shall use the single-underscore convention

Internal methods that are intended to be invoked from closely-coupled framework code (e.g. a `SuspenseElement` re-initializing a `Component` during SSR async resolution) SHALL be named with a single leading underscore (`_name`), not name-mangled double underscores (`__name`). Name-mangled (`__`-prefixed) identifiers encode the defining class name into the attribute, forcing callers to reach through the mangled form (e.g. `obj._Component__method`), which is a code smell, defeats static type checkers, and obscures intent. The single-underscore convention signals "protected: callable from within the framework, not part of the public API," matching actual usage. A `__`-prefixed name SHALL only be used when the method or attribute is genuinely private to its defining class and never referenced from another class.

#### Scenario: Component re-initialization is callable from Suspense via the protected name
- **WHEN** `SuspenseElement._resolve_component_templates` re-initializes a `Component` after resolving its async template
- **THEN** it SHALL call `component._init_component(component._property)` using the single-underscore name
- **AND** `uv run pyright` SHALL report no `reportAttributeAccessIssue` warning for the access
- **AND** the mangled form `_Component__init_component` SHALL no longer appear in the codebase

#### Scenario: Internal rename does not widen the public API
- **WHEN** `Component.__init_component` is renamed to `Component._init_component`
- **THEN** the method SHALL remain outside the documented public API (leading underscore)
- **AND** no new public method SHALL be introduced on `Component`