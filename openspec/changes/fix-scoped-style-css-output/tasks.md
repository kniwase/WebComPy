## 1. Core Implementation

- [ ] 1.1 Add `_classify_nested_key` helper function to categorize keys (at-rule/pseudo/combinator)
- [ ] 1.2 Update `_generate_css_recursive` to handle at-rules with wrapping structure
- [ ] 1.3 Update `_generate_css_recursive` to handle pseudo-selectors without space
- [ ] 1.4 Maintain combinator selector handling with space
- [ ] 1.5 Update `_process_style_declaration` to raise `TypeError` on unknown types

## 2. Specification Updates

- [ ] 2.1 Update `openspec/specs/components/spec.md` with correct CSS output examples
- [ ] 2.2 Verify all CSS examples use valid syntax (at-rule wrapping, pseudo no-space)

## 3. Unit Tests

- [ ] 3.1 Add unit test for `@media` at-rule wrapping output
- [ ] 3.2 Add unit test for `@supports` at-rule wrapping output
- [ ] 3.3 Add unit test for `:hover` pseudo-class (no space)
- [ ] 3.4 Add unit test for `::after` pseudo-element (no space)
- [ ] 3.5 Add unit test for `> li` combinator (with space)
- [ ] 3.6 Add unit test for deep nesting (at-rule with pseudo inside)
- [ ] 3.7 Add unit test for `TypeError` on invalid value types

## 4. E2E Test Enhancements

- [ ] 4.1 Update E2E test to verify `@media` CSS structure (not just presence)
- [ ] 4.2 Update E2E test to verify `:hover` actually works on hover
- [ ] 4.3 Add Playwright test for responsive behavior at different widths

## 5. Cleanup & Verification

- [ ] 5.1 Run `ruff check .` and fix any linting issues
- [ ] 5.2 Run `ruff format .` to ensure code formatting compliance
- [ ] 5.3 Verify all type checks pass with `pyright`
- [ ] 5.4 Run existing tests to ensure no regressions
- [ ] 5.5 Manually verify generated CSS in browser dev tools
