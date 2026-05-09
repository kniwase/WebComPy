## 1. Type System Updates

- [ ] 1.1 Define recursive `StyleDeclaration` type alias in `_generator.py`
- [ ] 1.2 Update `scoped_style` setter type signature to accept nested structure
- [ ] 1.3 Run `pyright` to verify type safety is maintained

## 2. Core Implementation

- [ ] 2.1 Extract CSS generation logic into separate helper function `_generate_css(selector, style_dict)`
- [ ] 2.2 Implement recursive processing to separate properties from nested rules
- [ ] 2.3 Implement selector concatenation for nested rules (e.g., parent + child selector)
- [ ] 2.4 Update `scoped_style` setter to call recursive generator
- [ ] 2.5 Verify backward compatibility with existing flat style definitions

## 3. Unit Testing

- [ ] 3.1 Create unit tests for `@media` query nesting
- [ ] 3.2 Create unit tests for pseudo-class nesting (`:hover`, `:focus`, etc.)
- [ ] 3.3 Create unit tests for deeply nested structures (2+ levels)
- [ ] 3.4 Create unit tests for combinator selectors in nested structure (`>`, `+`, `~`)
- [ ] 3.5 Create unit tests for backward compatibility (flat styles still work)
- [ ] 3.6 Run existing tests to ensure no regressions

## 4. E2E Testing

- [ ] 4.1 Create E2E test page demonstrating nested scoped styles
- [ ] 4.2 Add Playwright tests for responsive behavior (@media queries)
- [ ] 4.3 Add Playwright tests for interactive states (`:hover`, `:focus`)
- [ ] 4.4 Run full E2E test suite

## 5. Documentation & Examples

- [ ] 5.1 Update existing demo components to showcase nested styles (e.g., `todo.py`, `home.py`)
- [ ] 5.2 Add code examples to `docs_app` demonstrating common patterns

## 6. Cleanup & Verification

- [ ] 6.1 Run `ruff check .` and fix any linting issues
- [ ] 6.2 Run `ruff format .` to ensure code formatting compliance
- [ ] 6.3 Verify all type checks pass with `pyright`
- [ ] 6.4 Run full test suite with `pytest`
