## ADDED Requirements

### Requirement: The overview Purpose shall not enumerate missing capabilities

The Purpose section of `openspec/specs/overview/spec.md` SHALL describe
what the framework is and promises, and SHALL NOT maintain a list of
capabilities the framework lacks. Open work and known limitations SHALL be
tracked in `openspec/config.yaml` (Known Issues) or in OpenSpec change
proposals instead, so that capability claims cannot rot against implemented
specs.

#### Scenario: A gap list is proposed for the overview

- **WHEN** a change proposes adding or updating a "not yet provided" style
  enumeration in the overview Purpose section
- **THEN** the enumeration SHALL be rejected
- **AND** the gap SHALL be tracked in `openspec/config.yaml` Known Issues
  or in an OpenSpec change proposal instead

#### Scenario: A capability gains its own spec

- **WHEN** a capability is implemented and governed by its own spec (e.g.
  `di-injection`, `plugin-system`, `list-reconciliation`)
- **THEN** the overview Purpose section SHALL require no gap-list edit,
  because it does not track gaps
