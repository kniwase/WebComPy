## Why

The current nested scoped style implementation generates invalid CSS for `@media`/`@supports` at-rules and incorrect selector semantics for pseudo-classes. At-rules use space-concatenation (`.btn @media {...}`) instead of wrapping (`@media {... .btn {...}}`), and pseudo-classes add unwanted spaces (`.btn :hover` vs `.btn:hover`), causing styles to not work as expected.

## What Changes

- **Fixed**: `@media`, `@supports`, `@container` at-rules now generate valid wrapping CSS structure
- **Fixed**: Pseudo-classes (`:hover`, `:focus`) and pseudo-elements (`::before`, `::after`) concatenate without space
- **Fixed**: Combinator selectors (`>`, `+`, `~`, descendant space) maintain correct spacing
- **Modified**: `_generate_css_recursive` to detect at-rules vs pseudo-selectors vs combinators
- **Modified**: `components` spec requirements for scoped CSS output format
- **Added**: Unit tests validating generated CSS string format
- **Breaking**: CSS output format changes - existing nested styles will generate different (valid) CSS

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `components`: Update scoped CSS requirements to specify correct at-rule wrapping and pseudo-selector concatenation

## Impact

- **Breaking Change**: CSS output format changes for nested styles
  - At-rules: `.selector @media {...}` → `@media {... .selector {...}}`
  - Pseudo-classes: `.selector :hover` → `.selector:hover`
- **Code Changes**: `webcompy/components/_generator.py` - `_generate_css_recursive` function
- **Spec Changes**: `openspec/specs/components/spec.md` - Update CSS output examples
- **Tests**: Add unit tests for CSS string validation; enhance E2E tests

## Known Issues Addressed

This change addresses critical bugs identified in PR #151 review:
- Invalid CSS generation for at-rules (browsers ignore these rules)
- Incorrect pseudo-class semantics (targets descendants instead of element itself)

## Non-goals

- No changes to the scoping mechanism (`[webcompy-cid-{id}]` attribute)
- No changes to flat style definitions (backward compatible)
- No new CSS features beyond fixing the output format
- No performance optimizations
