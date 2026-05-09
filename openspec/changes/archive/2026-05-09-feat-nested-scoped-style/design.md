## Context

**Current State:**
The `scoped_style` property in `ComponentGenerator` accepts `dict[str, dict[str, str]]` — a flat structure where selectors map directly to CSS property declarations. The setter processes this into scoped CSS by prefixing selectors with `[webcompy-cid-{id}]` attribute selectors.

**Problem:**
This flat structure cannot express nested CSS rules like media queries or pseudo-class selectors without duplicating the parent selector:

```python
# Current limitation - cannot do this
{
    ".button": {
        "color": "blue",
        "@media (max-width: 768px)": {  # ❌ Not supported
            "color": "red",
        },
    },
}
```

**Constraints:**
- Must maintain backward compatibility with existing flat style definitions
- Type safety must be preserved (no `Any` or overly broad types)
- Implementation must work in both browser (PyScript) and server (SSG) contexts
- No changes to the CSS scoping mechanism (attribute-based isolation remains)

## Goals / Non-Goals

**Goals:**
- Support nested dictionaries for `@media`, `@supports`, and pseudo-class selectors
- Maintain full backward compatibility with existing flat style definitions
- Preserve type safety with recursive type definitions
- Generate valid, scoped CSS from nested structures

**Non-Goals:**
- CSS variable support or runtime theming
- `&` parent selector shorthand syntax
- Global (non-scoped) style definitions
- Performance optimizations (caching, memoization)

## Decisions

### Decision 1: Use recursive TypeAlias for type safety

**Approach:**
```python
StyleDeclaration: TypeAlias = str | dict[str, "StyleDeclaration"]
StyleDict: TypeAlias = dict[str, StyleDeclaration]
scoped_style: dict[str, StyleDict]
```

**Rationale:**
- Maintains type safety without requiring exhaustive CSS property definitions
- Python 3.12+ supports forward references in TypeAlias with string quotes
- More flexible than TypedDict approach (no need to predefine all CSS properties)
- Clearer than Protocol approach (which lacks runtime type checking)

**Alternatives Considered:**
- **TypedDict with explicit properties**: Too rigid, would require maintaining exhaustive CSS property list
- **Protocol**: Lacks runtime validation, type checking less precise
- **dataclass hierarchy**: Breaking change to existing API

### Decision 2: Recursive processing with selector accumulation

**Approach:**
```python
def _generate_css(selector: str, style_dict: StyleDict) -> str:
    properties = {}
    nested = {}
    
    for key, value in style_dict.items():
        if isinstance(value, dict):
            nested[key] = value  # @media, :hover, etc.
        else:
            properties[key] = value  # CSS properties
    
    # Generate base rule
    result = f"{selector} {{ {format_props(properties)} }}"
    
    # Recursively process nested rules
    for nested_selector, nested_styles in nested.items():
        combined = f"{selector} {nested_selector}"
        result += _generate_css(combined, nested_styles)
    
    return result
```

**Rationale:**
- Simple recursive algorithm handles arbitrary nesting depth
- Selector accumulation (`parent child` concatenation) works for all cases
- Minimal changes to existing CSS generation logic

**Alternatives Considered:**
- **Iterative with stack**: More complex, no clear benefit
- **AST-based parsing**: Overkill for this use case
- **Separate processing for @rules vs pseudo-classes**: Unnecessary complexity

### Decision 3: Preserve existing scoping mechanism

**Approach:**
The `[webcompy-cid-{id}]` attribute is inserted at the selector level, before any nested structure:

```python
# Input
{".button": {"color": "blue", "@media (...)": {"color": "red"}}}

# Output
.button[webcompy-cid-xxx] { color: blue; }
.button[webcompy-cid-xxx] @media (...) { color: red; }
```

**Rationale:**
- Maintains style isolation guarantees
- No changes required to component rendering logic
- Consistent with existing behavior

### Decision 4: No validation of nested selector syntax

**Approach:**
The implementation accepts any string as a nested selector without validating CSS syntax. Invalid selectors result in invalid CSS (user's responsibility).

**Rationale:**
- Keeps implementation simple
- CSS validation is complex and error-prone
- Browser CSS parser will ignore invalid rules anyway
- Developers can use browser dev tools to catch errors

**Alternatives Considered:**
- **Runtime validation**: Adds complexity, limited value
- **Linting tool**: Could be added later as separate feature

## Risks / Trade-offs

### Risk 1: Type checking limitations with recursive types

**Risk:** Pyright/MyPy may have difficulty inferring types for deeply nested structures.

**Mitigation:** 
- Test with both type checkers during implementation
- Add type annotations to helper functions
- Document expected type behavior in type comments if needed

### Risk 2: CSS output validity

**Risk:** Incorrect selector concatenation could produce invalid CSS (e.g., double `@media` nesting).

**Mitigation:**
- Add E2E tests for common patterns (@media, :hover, combinators)
- Manual verification of generated CSS in browser dev tools
- Document supported patterns in usage examples

### Risk 3: Performance with deeply nested structures

**Risk:** Recursive processing could be slow for very deep nesting.

**Mitigation:**
- Typical use cases have shallow nesting (1-2 levels)
- Can add depth limit if needed (not implemented initially)
- Profile performance during testing

### Trade-off: Type precision vs. flexibility

**Trade-off:** Using `TypeAlias` with `dict[str, ...]` allows any string key, not just valid CSS properties.

**Acceptable Because:**
- Runtime behavior is what matters (browser CSS parser validates)
- More flexible for future CSS features
- Consistent with existing type strategy in framework

## Migration Plan

**No migration required** — this change is fully backward compatible.

Existing flat style definitions continue to work:
```python
# Still valid
{".button": {"color": "blue"}}

# New capability
{".button": {"color": "blue", "@media (...)": {"color": "red"}}}
```

## Open Questions

None — implementation approach is clear.
