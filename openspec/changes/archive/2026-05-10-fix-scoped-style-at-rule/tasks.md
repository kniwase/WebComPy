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

## 6. Extended At-Rule Support

- [x] 6.1 Implement `_process_at_rule_inner` recursive method for nested at-rule handling
- [x] 6.2 Implement `_scope_combinator_selector` shared helper for consistent combinator scoping
- [x] 6.3 Add `@keyframes` special handling in getter (no cid on inner keys)
- [x] 6.4 Add `@keyframes` handling inside nested at-rules in `_process_at_rule_inner`
- [x] 6.5 Scope pseudo-class/element inside at-rules with `*[webcompy-cid-xxx]` prefix
- [x] 6.6 Fix orphan attribute selectors from combinator-first keys with `*[webcompy-cid-xxx]` guard
- [x] 6.7 Add defensive empty-string guard in `_generate_css_recursive` combinator branch
- [x] 6.8 Add unit tests: nested at-rules (1-3 levels), @keyframes, pseudo/combinator in at-rule, @keyframes inside @media
- [x] 6.9 Run all existing tests to verify no regressions

## 7. OpenSpec Artifact Updates

- [x] 7.1 Update design.md Goals/Non-Goals to reflect extended at-rule support
- [x] 7.2 Update design.md Decisions with new implementation details
- [x] 7.3 Update design.md Migration Plan with all supported CSS patterns
- [x] 7.4 Update delta spec with nested at-rule, @keyframes, pseudo/combinator requirements
- [x] 7.5 Update tasks.md with additional implementation tracks
