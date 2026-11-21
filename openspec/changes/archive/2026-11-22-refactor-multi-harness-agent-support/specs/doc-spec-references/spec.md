## MODIFIED Requirements

### Requirement: Universal docs shall reference specs instead of transcribing spec detail

`openspec/specs/` SHALL be the single source of truth for WebComPy requirements and API naming. Universal docs (`AGENTS.md`, `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, `openspec/SPEC_INDEX.md`, and `.agents/skills/*/SKILL.md`) SHALL NOT transcribe mutable specification prose or API enumerations, and SHALL reference the owning spec by path (e.g. `openspec/specs/reactive/spec.md`).

#### Scenario: Framework invariants are referenced, not transcribed

- **WHEN** a universal doc needs to convey a framework invariant (e.g. reactive contracts, error handling, hydration rules)
- **THEN** the doc SHALL present the invariant as a heading plus a reference to the owning spec file, and SHALL NOT restate the full requirement prose

#### Scenario: Reactive primitive names are referenced, not enumerated

- **WHEN** a universal doc's code-conventions section mentions reactive state primitives
- **THEN** the doc SHALL point to `openspec/specs/reactive/spec.md` (and `openspec/specs/composables/spec.md` as applicable) instead of enumerating mutable class names such as the retired `Reactive` alias

### Requirement: Checker script shall validate spec references and retired names

The stdlib-only checker (`scripts/check-doc-spec-refs.py`) SHALL scan universal docs (`AGENTS.md`, `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, `openspec/SPEC_INDEX.md`, `.agents/skills/*/SKILL.md`, and `docs_app/documents/*.md`) to verify every `openspec/specs/<name>` reference resolves and no retired API name appears. It SHALL exit non-zero when any violation is found.

#### Scenario: Dangling spec reference

- **WHEN** a universal doc references `openspec/specs/does-not-exist/spec.md`
- **THEN** the checker SHALL fail and list the missing spec path

#### Scenario: All references resolve and no retired names present

- **WHEN** every spec reference in the universal docs resolves and no retired API name remains
- **THEN** the checker SHALL exit success with no findings

### Requirement: Spec changes shall trigger reference maintenance

When a spec is added or removed, the referencing universal docs SHALL be updated accordingly and the checker SHALL be run. The `AGENTS.md` "Review Knowledge Maintenance" section SHALL enumerate this obligation.

#### Scenario: Spec removal leaves a dangling reference

- **WHEN** a spec is removed from `openspec/specs/` but a universal doc still references it
- **THEN** the checker SHALL fail on the dangling reference until the doc is updated

#### Scenario: Spec addition is referenced

- **WHEN** a new spec is added to `openspec/specs/`
- **THEN** the "Current Specs" list in `openspec/SPEC_INDEX.md` SHALL be updated with the new entry

## ADDED Requirements

### Requirement: AGENTS.md shall stay within cross-harness rule size limits

`AGENTS.md` UTF-8 byte size SHALL NOT exceed 24,000 bytes so rule loaders with per-file caps (such as Antigravity) ingest the entire file without truncation. Mutable spec navigation indexes (`Framework Invariants`, `File → Spec Mapping`, `Current Specs`) SHALL live in `openspec/SPEC_INDEX.md`, and `scripts/check-doc-spec-refs.py` SHALL enforce the byte limit.

#### Scenario: AGENTS.md exceeds 24,000 bytes

- **WHEN** `AGENTS.md` exceeds 24,000 UTF-8 bytes
- **THEN** `scripts/check-doc-spec-refs.py` SHALL report a violation and exit non-zero

#### Scenario: AGENTS.md within size cap

- **WHEN** `AGENTS.md` is at or below 24,000 UTF-8 bytes
- **THEN** the byte-cap check in `scripts/check-doc-spec-refs.py` SHALL pass

### Requirement: Harness skill and command symlink mirrors shall stay in parity with SSOT

`CLAUDE.md` SHALL be a relative symlink to `AGENTS.md`. `.claude/skills/`, `.claude/commands/`, and `.opencode/commands/` SHALL be physical directories whose entries are non-dangling relative symlinks matching `.agents/skills/` and `.agents/commands/` 1-to-1. `scripts/check-doc-spec-refs.py` SHALL verify symlink targets, directory types, and parity.

#### Scenario: Missing or extra symlink in mirror directory

- **WHEN** a skill or command exists in `.agents/` without a matching relative symlink in its mirror directory (or an extra entry exists in the mirror)
- **THEN** `scripts/check-doc-spec-refs.py` SHALL report the mismatch and exit non-zero

#### Scenario: Parent mirror directory is itself a symlink or entry is broken

- **WHEN** `CLAUDE.md` is not a valid relative symlink to `AGENTS.md`, a mirror directory itself is a symlink, or any symlink target is broken or does not resolve to the SSOT entry
- **THEN** `scripts/check-doc-spec-refs.py` SHALL report the error and exit non-zero

#### Scenario: All mirror symlinks match SSOT

- **WHEN** `CLAUDE.md` links to `AGENTS.md` and all three mirror directories are physical directories whose entries match `.agents/` 1-to-1 via valid relative symlinks
- **THEN** the mirror parity check in `scripts/check-doc-spec-refs.py` SHALL pass
