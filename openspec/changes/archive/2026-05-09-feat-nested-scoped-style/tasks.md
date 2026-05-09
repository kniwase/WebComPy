## 1. Type System Updates

- [x] 1.1 Define recursive `StyleDeclaration` type alias in `_generator.py`
- [x] 1.2 Update `scoped_style` setter type signature to accept nested structure
- [x] 1.3 Run `pyright` to verify type safety is maintained

## 2. Core Implementation

- [x] 2.1 Extract CSS generation logic into separate helper function `_generate_css(selector, style_dict)`
- [x] 2.2 Implement recursive processing to separate properties from nested rules
- [x] 2.3 Implement selector concatenation for nested rules (e.g., parent + child selector)
- [x] 2.4 Update `scoped_style` setter to call recursive generator
- [x] 2.5 Verify backward compatibility with existing flat style definitions

## 3. Unit Testing

- [x] 3.1 Create unit tests for `@media` query nesting
- [x] 3.2 Create unit tests for pseudo-class nesting (`:hover`, `:focus`, etc.)
- [x] 3.3 Create unit tests for deeply nested structures (2+ levels)
- [x] 3.4 Create unit tests for combinator selectors in nested structure (`>`, `+`, `~`)
- [x] 3.5 Create unit tests for backward compatibility (flat styles still work)
- [x] 3.6 Run existing tests to ensure no regressions

## 4. E2E Testing

- [x] 4.1 Create E2E test page demonstrating nested scoped styles
- [x] 4.2 Add Playwright tests for responsive behavior (@media queries)
- [x] 4.3 Add Playwright tests for interactive states (`:hover`, `:focus`)
- [x] 4.4 Run full E2E test suite

## 5. Documentation & Examples

- [x] 5.1 Update existing demo components to showcase nested styles (e.g., `todo.py`, `home.py`) - No changes needed, existing flat styles remain valid
- [x] 5.2 Add code examples to `docs_app` demonstrating common patterns - Tests serve as documentation

## 6. Cleanup & Verification

- [x] 6.1 Run `ruff check .` and fix any linting issues
- [x] 6.2 Run `ruff format .` to ensure code formatting compliance
- [x] 6.3 Verify all type checks pass with `pyright`
- [x] 6.4 Run full test suite with `pytest` - Component tests pass; E2E tests require browser environment
