# api-docstrings (delta)

## Purpose

Governs docstring coverage and content for the public interfaces of the `webcompy`, `webcompy-server`, `webcompy-cli`, and `webcompy-testing` packages, and provides a machine-checkable guardrail so coverage cannot regress and docstrings or comments never leak OpenSpec project-management artifacts.

## ADDED Requirements

### Requirement: Public interfaces shall carry docstrings

Every public interface of the four packages under `packages/` SHALL have a docstring. The public interface is defined as: (1) every name re-exported through any package or subpackage `__init__.py`, resolved to its definition site including private `_*.py` modules; (2) all public methods and properties of re-exported classes; (3) a one-line summary docstring on every module under `packages/*/src`; (4) PEP 224-style attribute docstrings on public module-level constants; and (5) an explicit allowlist of important internal interfaces maintained in the checker. Docstrings SHALL be written in English.

#### Scenario: Re-exported function without docstring

- **WHEN** a name is re-exported from a package `__init__.py` and its definition site has no docstring
- **THEN** the docstring checker SHALL report a violation and exit non-zero

#### Scenario: Public constant without attribute docstring

- **WHEN** a public (non-underscore) module-level constant lacks a string literal immediately following its assignment
- **THEN** the docstring checker SHALL report a violation

#### Scenario: Definition exempted by convention

- **WHEN** a definition is a dunder method, a nested function, an `@overload` stub (docstring lives on the implementation), or a property setter/deleter (docstring lives on the getter)
- **THEN** the checker SHALL NOT require a docstring for it, and `__init__` parameters SHALL be documented in the class docstring's `Args:` section instead of a method docstring

### Requirement: Docstrings shall follow Google style conventions

Module docstrings SHALL be a summary (one or more prose lines, no section headers). Public function and method docstrings SHALL document parameters in `Args:` and the result in `Returns:`, plus `Raises:` when raising is part of the contract. Public class docstrings SHALL document constructor parameters in `Args:` and public instance attributes and properties in `Attributes:`. Structural completeness (Args entries matching the signature, Attributes completeness) SHALL be verified in AI code review as a mandatory perspective.

#### Scenario: New public function missing parameter documentation

- **WHEN** a PR adds or modifies a public function whose docstring omits parameters present in the signature
- **THEN** the AI code review SHALL flag the gap as a must-fix item

### Requirement: Docstrings and comments shall not reference OpenSpec artifacts

Docstrings and code comments under `packages/*/src` SHALL NOT reference OpenSpec project-management artifacts: `openspec/` paths, spec or change names, `spec.md`/`tasks.md`/`proposal.md`/`design.md` files, requirement or scenario identifiers, and task numbers. Docstrings describe the code itself. References to external standards (for example RFCs, CommonMark, PEPs) remain allowed.

#### Scenario: Comment referencing an OpenSpec change

- **WHEN** a comment or docstring contains an `openspec/` path or an OpenSpec change or spec reference
- **THEN** the docstring checker SHALL report a violation and exit non-zero

### Requirement: Docstring coverage shall be enforced by a checker with a migration baseline

The repository SHALL provide a stdlib-only checker at `scripts/check-docstrings.py` that verifies this spec's requirements and exits non-zero with a concise report on any violation. During migration, a baseline file SHALL list pre-existing gaps: an undocumented symbol absent from the baseline SHALL fail, and a baseline entry whose symbol now has a docstring SHALL fail (forcing baseline shrinkage). When no gaps remain, the baseline file SHALL be deleted and the checker SHALL run strict. The checker SHALL run in CI and in the documented local CI workflow.

#### Scenario: New code without docstring during migration

- **WHEN** the baseline is non-empty and a new undocumented in-scope definition is added
- **THEN** CI SHALL fail because the symbol is not in the baseline

#### Scenario: Completed item removed from baseline

- **WHEN** a symbol listed in the baseline gains a docstring
- **THEN** CI SHALL fail until the baseline entry is removed, guaranteeing monotonic shrinkage

### Requirement: The docstring rule shall be recorded in project governance docs

The docstring requirement and the OpenSpec-reference ban SHALL be recorded in `AGENTS.md` code conventions (amending the "no comments unless requested" convention to carve out required docstrings), in `openspec/config.yaml` context or rules, and as mandatory review perspectives in the `webcompy-review` skill, so both human and AI contributors are bound by the same rule.

#### Scenario: AI review checks docstring compliance

- **WHEN** a PR modifies files under `packages/*/src`
- **THEN** the AI review SHALL verify docstring presence on new or modified public interfaces, Google-style structural completeness, and the absence of OpenSpec artifact references
