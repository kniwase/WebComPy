## 1. Core Implementation

- [ ] 1.1 Update `scoped_style` setter to detect at-rule keys using `_classify_nested_key`
- [ ] 1.2 Skip cid application for at-rule keys (preserve as-is)
- [ ] 1.3 Apply cid application to non-at-rule keys (existing behavior)
- [ ] 1.4 Verify existing nested at-rule tests still pass

## 2. Unit Tests

- [ ] 2.1 Add unit test for top-level `@media` at-rule
- [ ] 2.2 Add unit test for top-level `@supports` at-rule
- [ ] 2.3 Add unit test for at-rule with leading whitespace
- [ ] 2.4 Add unit test verifying at-rule itself is NOT scoped
- [ ] 2.5 Add unit test verifying selectors inside at-rule ARE scoped
- [ ] 2.6 Run all existing tests to verify no regressions

## 3. E2E Tests

- [ ] 3.1 Add E2E test page with top-level at-rule styles
- [ ] 3.2 Add E2E test verifying CSS output structure (at-rule syntax valid)
- [ ] 3.3 Add E2E test verifying responsive behavior at different viewport widths
- [ ] 3.4 Run full E2E test suite

## 4. Specification Updates

- [ ] 4.1 Update `openspec/specs/components/spec.md` with at-rule key requirement
- [ ] 4.2 Add scenario for top-level at-rule usage
- [ ] 4.3 Add scenario for at-rule detection with whitespace
- [ ] 4.4 Verify all CSS examples use valid syntax

## 5. Cleanup & Verification

- [ ] 5.1 Run `ruff check .` and fix any linting issues
- [ ] 5.2 Run `ruff format .` to ensure code formatting compliance
- [ ] 5.3 Run `pyright` to verify type checking passes
- [ ] 5.4 Manually verify generated CSS in browser dev tools
- [ ] 5.5 Document change in release notes (bug fix)
