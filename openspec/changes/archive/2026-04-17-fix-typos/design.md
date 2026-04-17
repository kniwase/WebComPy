## Context

The codebase has four consistent typos in internal API names that are used across multiple modules:
- `_get_evnet` in the reactive system (20 occurrences across 5 files)
- `__webcompy_componet_definition__` and `componet_generator` in the component system (3 occurrences across 2 files)
- `__conponents` in the component store (5 occurrences in 1 file)

These are all internal (private/dunder) names with no public API exposure.

## Goals / Non-Goals

**Goals:**
- Correct all typo-named internal identifiers to their intended English spellings
- Ensure all references (definitions, usages, stub files, tests) are updated atomically

**Non-Goals:**
- Changing any external or public API behavior
- Refactoring the underlying patterns (e.g., replacing decorator patterns, adding DI)
- Adding backwards compatibility aliases for the old misspelled names (these are internal-only APIs)

## Decisions

### 1. Direct rename without deprecation aliases

**Decision**: Rename all identifiers in-place without keeping backward-compatible aliases.

**Rationale**: All affected names are private (`_get_evnet` is a classmethod decorator starting with underscore; `__webcompy_componet_definition__` and `__conponents` are dunder/mangled names). No external consumer depends on these names. Adding aliases would add dead code.

**Alternatives**: Add `getattr(cls, '_get_evnet', _get_event)` style compat shims — rejected because no external consumers exist.

### 2. Use find-and-replace across the entire codebase

**Decision**: Perform whole-project search-and-replace for each typo, covering `.py`, `.pyi`, and test files in a single pass.

**Rationale**: These are simple identifier renames with no logic changes. A systematic replace-all ensures nothing is missed.

**Alternatives**: Manual per-file edits — rejected as error-prone and slower.

## Risks / Trade-offs

- **[Risk]** Downstream consumers who may have accessed internal APIs by misspelled name → **Mitigation**: These are all private/dunder names; no public API contract is broken. The `__webcompy_componet_definition__` dunder is the most likely to be accessed externally, but it's an internal protocol attribute.
- **[Risk]** Merge conflicts on in-flight PRs → **Mitigation**: This is a simple rename; conflict resolution is straightforward with search-and-replace.