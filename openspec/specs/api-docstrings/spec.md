# api-docstrings Specification

## Purpose

Public interfaces under `packages/*/src` carry docstrings as the user-facing API documentation. This capability requires that docstrings stay synchronized with the implementation: any modification to a public interface's behavior, signature, or contract SHALL be reflected in its docstring within the same PR. Docstring-implementation inconsistency blocks approval, with pydoclint enforcing structural (Args/Returns/Raises) agreement mechanically and AI review catching semantic drift.

## Requirements

### Requirement: Docstrings shall remain consistent with implementation

Docstrings for public interfaces SHALL accurately describe the current implementation including behavior, parameters, return values, raised exceptions, and attributes. WHEN the implementation of a public interface is modified, its docstring SHALL be updated in the same PR. Inconsistency between implementation and docstring SHALL be treated as a must-fix and the PR SHALL NOT be approved.

#### Scenario: Implementation behavior changes without docstring update

- **WHEN** a PR modifies the logic or contract of a public function/class but leaves its summary/Args/Returns/Raises/Attributes unchanged
- **THEN** AI code review SHALL flag the inconsistency as a must-fix item and the PR SHALL NOT be approved

#### Scenario: Signature changes without docstring update

- **WHEN** a public function gains, removes, or renames a parameter or changes its return/exception contract without updating the docstring
- **THEN** CI (pydoclint) SHALL fail on mismatched Args/Returns/Raises and AI review SHALL flag the gap as must-fix
