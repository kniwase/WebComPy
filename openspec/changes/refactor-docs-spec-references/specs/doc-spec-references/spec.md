## ADDED Requirements

### Requirement: Universal docs shall reference specs instead of transcribing spec detail

`openspec/specs/` SHALL be the single source of truth for WebComPy requirements and API naming. The universal documentation files (`AGENTS.md`, `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, and `.opencode/skills/*/SKILL.md`) SHALL NOT transcribe mutable specification content (requirement prose, invariant detail, or API-name enumerations). Where such content is needed, these docs SHALL reference the owning spec by path (e.g. `openspec/specs/reactive/spec.md`).

#### Scenario: Framework invariants are referenced, not transcribed

- **WHEN** a universal doc needs to convey a framework invariant (e.g. reactive contracts, error handling, hydration rules)
- **THEN** the doc SHALL present the invariant as a heading plus a reference to the owning spec file, and SHALL NOT restate the full requirement prose

#### Scenario: Reactive primitive names are referenced, not enumerated

- **WHEN** a universal doc's code-conventions section mentions reactive state primitives
- **THEN** the doc SHALL point to `openspec/specs/reactive/spec.md` (and `openspec/specs/composables/spec.md` as applicable) instead of enumerating mutable class names such as the retired `Reactive` alias

### Requirement: Retired API names shall not reappear in universal docs

The retired `Reactive`-family API names (`webcompy.reactive`, `ReactiveBase`, `Reactive(...)`, `Reactive[...]`, `ReactiveNode`, `ReactiveEdge`, `ReactiveReceivable`, `ReadonlyReactive`, `__reactive_members__`) SHALL NOT appear in the universal documentation files. The current names (`Signal`, `SignalBase`, `SignalNode`, `SignalEdge`, `SignalReceivable`, `ReadonlySignal`) SHALL be used instead.

#### Scenario: Stale Reactive reference in a skill file

- **WHEN** any universal doc contains `Reactive(0)`, `Reactive[T]`, `ReactiveBase`, or `webcompy.reactive`
- **THEN** the checker script SHALL report an error

#### Scenario: Rename introduces a new retired name

- **WHEN** a future change renames a public API
- **THEN** the old name SHALL be added to the checker's blocklist so docs referencing it fail validation

### Requirement: Checker script shall validate spec references and retired names

The repository SHALL provide a stdlib-only checker (`scripts/check-doc-spec-refs.py`) that scans the universal documentation files and validates: (1) every `openspec/specs/<name>` reference resolves to an existing `openspec/specs/<name>/spec.md`, and (2) no retired API name from the blocklist appears outside the checker's own source. The checker SHALL exit non-zero with a concise report when any violation is found.

#### Scenario: Dangling spec reference

- **WHEN** a universal doc references `openspec/specs/does-not-exist/spec.md`
- **THEN** the checker SHALL fail and list the missing spec path

#### Scenario: All references resolve and no retired names present

- **WHEN** every spec reference in the universal docs resolves and no retired API name remains
- **THEN** the checker SHALL exit success with no findings

### Requirement: Spec changes shall trigger reference maintenance

When a spec is added or removed, the referencing universal docs SHALL be updated accordingly and the checker SHALL be run. The AGENTS.md "Review Knowledge Maintenance" section SHALL enumerate this obligation.

#### Scenario: Spec removal leaves a dangling reference

- **WHEN** a spec is removed from `openspec/specs/` but a universal doc still references it
- **THEN** the checker SHALL fail on the dangling reference until the doc is updated

#### Scenario: Spec addition is referenced

- **WHEN** a new spec is added to `openspec/specs/`
- **THEN** the "Current Specs" list in AGENTS.md SHALL be updated with the new entry