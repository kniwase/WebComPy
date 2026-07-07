## ADDED Requirements

### Requirement: ReactiveList and ReactiveDict usage shall be audited

A comprehensive audit SHALL be performed of all usages of `ReactiveList` and `ReactiveDict` across the codebase, including framework internals, docs_app, tests, and examples. Each usage site SHALL be categorized by mutation pattern (method-level vs. whole-value), collection size sensitivity, and readability impact.

The audit results SHALL be documented in the change's design.md as a table with columns: file, usage pattern, collection type, mutation frequency, and migration feasibility.

#### Scenario: All usage sites are identified
- **WHEN** the audit is complete
- **THEN** every `ReactiveList` and `ReactiveDict` instantiation and mutation in the codebase SHALL be listed
- **AND** each usage SHALL be categorized by migration feasibility (easy, moderate, hard, blocking)

#### Scenario: Migration patterns are documented
- **WHEN** the audit identifies usage sites that can migrate to `Signal[list]` / `Signal[dict]`
- **THEN** before/after code examples SHALL be documented for each migration pattern
- **AND** common patterns (append, remove, update item, bulk replace) SHALL have documented equivalents

### Requirement: A deprecation recommendation shall be produced

Based on the audit, a clear recommendation SHALL be produced in design.md with one of three outcomes: **Deprecate** (remove ReactiveList/Dict in a future change), **Retain** (keep with current API), or **Partial Deprecate** (retain core functionality, remove rarely-used features).

The recommendation SHALL include rationale based on: migration feasibility percentage, DX impact assessment, performance considerations, and ecosystem alignment with Vue/Angular/Svelte.

#### Scenario: Recommendation is clear and actionable
- **WHEN** the investigation is complete
- **THEN** design.md SHALL contain a "Recommendation" section
- **AND** the recommendation SHALL be one of: Deprecate, Retain, Partial Deprecate
- **AND** the rationale SHALL reference specific audit findings

#### Scenario: Blocking dependencies are identified
- **WHEN** the investigation identifies usage sites that cannot migrate (e.g., `dict-repeat-overload` spec depends on ReactiveDict)
- **THEN** these blocking dependencies SHALL be explicitly listed
- **AND** the recommendation SHALL account for them (either Retain, or plan to remove the dependency first)
