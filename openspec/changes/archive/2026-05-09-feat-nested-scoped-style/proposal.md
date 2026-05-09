## Why

Scoped CSS currently supports only flat style declarations, making it impossible to write responsive styles with `@media` queries or nested pseudo-class selectors. Developers must either duplicate selectors or move styles outside the component, breaking encapsulation. This change enables nested style structures while maintaining strong type safety.

## What Changes

- **New**: Nested dictionary support in `scoped_style` for `@media`, `@supports`, and pseudo-class selectors
- **New**: Recursive type definition `StyleDeclaration = str | dict[str, StyleDeclaration]` for type-safe nested styles
- **Modified**: `ComponentGenerator.scoped_style` setter to recursively process nested style dictionaries
- **Modified**: CSS generation logic to flatten nested structures into valid CSS rules
- **Non-breaking**: Existing flat style definitions continue to work unchanged

## Capabilities

### New Capabilities
- `nested-scoped-style`: Support for nested style dictionaries in scoped_style, enabling @media queries, @supports, and pseudo-class selectors within component-scoped CSS

### Modified Capabilities
- `components`: Updates to scoped CSS requirement to support nested style structures while maintaining attribute-based scoping

## Impact

- **Type System**: Introduction of recursive type alias in `webcompy/components/_generator.py`
- **Runtime**: Recursive processing of style dictionaries in the `scoped_style` setter
- **CSS Output**: Generated CSS will include nested rules (e.g., `.btn[webcompy-cid-xxx] @media (...) { ... }`)
- **Backward Compatibility**: Fully backward compatible — existing flat style definitions remain valid
- **Dependencies**: None — pure framework enhancement

## Known Issues Addressed

None directly — this change addresses a feature gap, not a known bug.

## Non-goals

- **CSS-in-JS features**: This change does not add CSS variable support, style functions, or runtime theming
- **Performance optimization**: No caching or memoization of generated CSS — handled in future changes if needed
- **Selector shorthand**: The `&` parent selector syntax is out of scope (e.g., `&:hover` shorthand)
- **Global styles**: This change does not provide a mechanism for global (non-scoped) CSS
