## Context

**Current State:**
The `_generate_css_recursive` function uses simple space-concatenation for all nested keys:
```python
combined = f"{selector} {nested_selector}"
```

This produces:
- `.btn[webcompy-cid-xxx] @media (max-width: 768px) { color: red; }` — Invalid CSS
- `.btn[webcompy-cid-xxx] :hover { background: yellow; }` — Wrong semantics

**Problem:**
1. **At-rules** (`@media`, `@supports`, `@container`) must wrap selectors, not follow them
2. **Pseudo-selectors** (`:hover`, `:focus`, `::before`, `::after`) must attach directly without space
3. **Combinators** (`>`, `+`, `~`, descendant space) correctly use space

**Constraints:**
- Must maintain backward compatibility with flat style definitions
- Must preserve scoping mechanism (`[webcompy-cid-{id}]`)
- Type safety must be maintained

## Goals / Non-Goals

**Goals:**
- Generate valid CSS for at-rules (wrapping structure)
- Generate correct pseudo-selector semantics (no space)
- Maintain combinator selector behavior (space preserved)
- Update specs to reflect correct CSS output
- Add unit tests for CSS string validation

**Non-Goals:**
- No changes to scoping mechanism
- No new CSS features
- No performance optimizations
- No changes to flat style handling

## Decisions

### Decision 1: Categorize nested keys by prefix/pattern

**Approach:**
```python
def _classify_nested_key(key: str) -> Literal["at-rule", "pseudo", "combinator"]:
    if key.startswith("@"):
        return "at-rule"
    elif key.startswith(":") or key.startswith("::"):
        return "pseudo"
    else:
        return "combinator"
```

**Rationale:**
- Simple string prefix detection is reliable
- CSS syntax rules are clear: `@` for at-rules, `:` for pseudo
- No regex overhead needed

**Alternatives Considered:**
- **Regex pattern matching**: More complex, no clear benefit
- **Whitelist of known at-rules**: Less flexible for future CSS features
- **CSS parser**: Overkill for this use case

### Decision 2: Separate processing paths per category

**Approach:**
```python
if key.startswith("@"):
    # At-rule: wrap selector inside
    # @media (...) { selector { props } }
elif key.startswith(":"):
    # Pseudo: concatenate without space
    # selector:pseudo { props }
else:
    # Combinator: concatenate with space
    # selector combinator { props }
```

**Rationale:**
- Clear separation of concerns
- Each category has distinct CSS syntax rules
- Easy to extend for new categories

### Decision 3: At-rule wrapping requires nested CSS generation

**Approach:**
For at-rules, generate the wrapper first, then recursively generate selectors inside:
```python
def _generate_at_rule(at_rule: str, selector: str, style_dict: dict) -> str:
    inner_css = _generate_css_recursive(selector, style_dict)
    return f"{at_rule} {{ {inner_css} }}"
```

**Example:**
```python
# Input
{".btn": {"@media (max-width: 768px)": {"color": "red"}}}

# Output
@media (max-width: 768px) { .btn[webcompy-cid-xxx] { color: red; } }
```

**Rationale:**
- Matches CSS at-rule syntax
- Allows nested pseudo-selectors inside at-rules
- Recursive approach handles arbitrary nesting depth

### Decision 4: Pseudo-selector concatenation without space

**Approach:**
```python
if key.startswith(":"):
    combined = f"{selector}{key}"  # No space
```

**Example:**
```python
# Input
{".btn": {":hover": {"background": "yellow"}}}

# Output
.btn[webcompy-cid-xxx]:hover { background: yellow; }
```

**Rationale:**
- Correct CSS pseudo-class/element syntax
- Matches developer expectations
- Fixes semantic bug (descendant vs self)

### Decision 5: Maintain combinator behavior

**Approach:**
Keep existing space-concatenation for combinators:
```python
else:  # combinator
    combined = f"{selector} {key}"
```

**Rationale:**
- Current behavior is correct for combinators
- `.menu > li` requires space before `>`
- `.parent .child` requires space between selectors

### Decision 6: Error on unknown value types

**Approach:**
```python
def _process_style_declaration(declaration: dict[str, StyleDeclaration]) -> dict[str, StyleDeclaration]:
    for key, value in declaration.items():
        if isinstance(value, dict):
            result[key] = _process_style_declaration(value)
        elif isinstance(value, str):
            result[key] = value.strip().rstrip(";").rstrip()
        else:
            raise TypeError(f"Invalid style value type: {type(value)}")
```

**Rationale:**
- Fail fast on bugs
- Clear error messages
- Type safety enforcement

## Risks / Trade-offs

### Risk 1: Breaking change in CSS output

**Risk:** Existing nested styles will generate different CSS output.

**Mitigation:**
- Document breaking change in changelog
- Provide migration examples
- The new output is valid CSS (old was invalid), so this is a bug fix

### Risk 2: Complex nested at-rules

**Risk:** Deeply nested at-rules (e.g., `@media` inside `@supports`) may be complex.

**Mitigation:**
- Recursive approach handles arbitrary depth
- Add tests for deep nesting
- Typical use cases are 1-2 levels

### Risk 3: Performance with many at-rules

**Risk:** Wrapping structure may generate more CSS text.

**Mitigation:**
- Typical use cases have few at-rules
- CSS size increase is minimal
- Correctness over optimization

### Trade-off: Detection simplicity vs. robustness

**Trade-off:** String prefix detection (`startswith("@")`) is simple but may not catch all edge cases.

**Acceptable Because:**
- CSS syntax is well-defined
- Developers use standard syntax
- Can add regex validation later if needed

## Migration Plan

**Breaking Change:** CSS output format changes for nested styles.

**Before (Invalid):**
```css
.btn[webcompy-cid-xxx] @media (max-width: 768px) { color: red; }
.btn[webcompy-cid-xxx] :hover { background: yellow; }
```

**After (Valid):**
```css
@media (max-width: 768px) { .btn[webcompy-cid-xxx] { color: red; } }
.btn[webcompy-cid-xxx]:hover { background: yellow; }
```

**Steps:**
1. Update `_generate_css_recursive` implementation
2. Update specs with correct CSS examples
3. Add unit tests for CSS string validation
4. Update E2E tests to verify actual behavior
5. Document breaking change in release notes

**Rollback:** Revert to previous implementation (but CSS will be invalid again)

## Open Questions

None — implementation approach is clear from PR review feedback.
