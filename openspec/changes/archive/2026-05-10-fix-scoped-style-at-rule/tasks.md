## 1. Core Implementation

- [x] 1.1 Update `scoped_style` setter to detect at-rule keys using `_classify_nested_key`
- [x] 1.2 Skip cid application for at-rule keys (preserve as-is)
- [x] 1.3 Apply cid application to non-at-rule keys (existing behavior)
- [x] 1.4 Verify existing nested at-rule tests still pass

## 2. Unit Tests

- [x] 2.1 Add unit test for top-level `@media` at-rule
- [x] 2.2 Add unit test for top-level `@supports` at-rule
- [x] 2.3 Add unit test for at-rule with leading whitespace
- [x] 2.4 Add unit test verifying at-rule itself is NOT scoped
- [x] 2.5 Add unit test verifying selectors inside at-rule ARE scoped
- [x] 2.6 Run all existing tests to verify no regressions

## 3. E2E Tests

- [x] 3.1 Add E2E test page with top-level at-rule styles
- [x] 3.2 Add E2E test verifying CSS output structure (at-rule syntax valid)
- [x] 3.3 Add E2E test verifying responsive behavior at different viewport widths
- [x] 3.4 Run full E2E test suite

## 4. Specification Updates

- [x] 4.1 Update `openspec/specs/components/spec.md` with at-rule key requirement
- [x] 4.2 Add scenario for top-level at-rule usage
- [x] 4.3 Add scenario for at-rule detection with whitespace
- [x] 4.4 Verify all CSS examples use valid syntax

## 5. Cleanup & Verification

- [x] 5.1 Run `ruff check .` and fix any linting issues
- [x] 5.2 Run `ruff format .` to ensure code formatting compliance
- [x] 5.3 Run `pyright` to verify type checking passes
- [x] 5.4 Manually verify generated CSS in browser dev tools
- [x] 5.5 Document change in release notes (bug fix)
