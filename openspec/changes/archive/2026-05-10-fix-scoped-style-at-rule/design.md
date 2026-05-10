## Context

**Current State:**

The `scoped_style` setter in `ComponentGenerator` (lines 158-169 of `_generator.py`) applies cid scoping to all keys:

```python
@scoped_style.setter
def scoped_style(self, style: dict[str, StyleDict]):
    cid = self._id
    self._style = dict(
        zip(
            (
                "".join(
                    f"{selector}[webcompy-cid-{cid}]{combinator}"
                    for selector, combinator in zip(...)
                )
                for selector in map(lambda s: s.strip(), style.keys())  # ← ALL keys get cid
            ),
            (_process_style_declaration(declaration) for declaration in style.values()),
            strict=True,
        )
    )
```

**Problem:**

When a developer uses an at-rule as a top-level key:

```python
Component.scoped_style = {
    " @media (max-width: 768px)": {  # ← This key
        " nav button": {"display": "block"},
    },
}
```

The setter applies cid scoping:

```python
# Current behavior (BUG):
" @media (max-width: 768px)" → "@media[webcompy-cid-xxx] (max-width:[webcompy-cid-xxx] 768px)[webcompy-cid-xxx]"
```

This corrupts the at-rule syntax before it even reaches `_generate_css_recursive`.

**Previous Fix Context:**

The change `2026-05-10-fix-scoped-style-css-output` fixed the CSS generation for **nested** at-rules:

```python
# This works correctly (nested at-rule):
{".btn": {"@media (...)": {"color": "red"}}}
# → @media (...) { .btn[webcompy-cid-xxx] { color: red; } }
```

But the setter still corrupts **top-level** at-rules:

```python
# This is broken (top-level at-rule):
{"@media (...)": {".btn": {"color": "red"}}}
# → @media[webcompy-cid-xxx] (...) [CORRUPTED]
```

**Constraints:**

- Must preserve backward compatibility with existing nested at-rule usage
- Must work with all CSS at-rules (`@media`, `@supports`, `@container`, `@keyframes`, etc.)
- Simple detection: `key.strip().startswith("@")`
- No changes to `_generate_css_recursive` required (it already handles at-rules correctly)

## Goals / Non-Goals

**Goals:**

- Detect at-rule keys in `scoped_style` setter
- Skip cid application for at-rule keys
- Preserve at-rule keys unchanged
- Apply cid to selectors inside at-rule blocks (handled by existing logic)
- Add unit tests for top-level at-rule
- Update specs with requirement

**Non-Goals:**

- No changes to `_generate_css_recursive` implementation
- No nested at-rule support (at-rule inside at-rule)
- No CSS parsing beyond prefix detection
- No changes to pseudo-class or combinator handling

## Decisions

### Decision 1: Use `_classify_nested_key` for at-rule detection

**Approach:**

Reuse the existing `_classify_nested_key` helper function:

```python
from webcompy.components._generator import _classify_nested_key

for selector in map(lambda s: s.strip(), style.keys()):
    if _classify_nested_key(selector) == "at-rule":
        # Skip cid application, use selector as-is
        processed_selector = selector
    else:
        # Apply cid scoping as before
        processed_selector = "".join(
            f"{selector}[webcompy-cid-{cid}]{combinator}"
            for selector, combinator in zip(...)
        )
```

**Rationale:**

- Function already exists and correctly identifies at-rules
- Single source of truth for key classification
- Consistent with `_generate_css_recursive` logic

**Alternatives Considered:**

- **Inline check**: `if selector.strip().startswith("@")` — simpler but duplicates logic
- **New helper**: `_is_at_rule(key)` — unnecessary abstraction
- **Regex**: Overkill for simple prefix detection

### Decision 2: Preserve at-rule keys unchanged

**Approach:**

When an at-rule is detected, use the key as-is without cid application:

```python
style_items = []
for selector, declaration in style.items():
    if _classify_nested_key(selector.strip()) == "at-rule":
        processed_selector = selector  # No cid
    else:
        processed_selector = "".join(
            f"{selector}[webcompy-cid-{cid}]{combinator}"
            for selector, combinator in zip(...)
        )
    style_items.append((processed_selector, _process_style_declaration(declaration)))

self._style = dict(style_items)
```

**Example:**

```python
# Input
{
    " nav": {"display": "flex"},
    " @media (max-width: 768px)": {" nav button": {"display": "block"}},
}

# After setter processing
{
    " nav[webcompy-cid-xxx]": {"display": "flex"},
    " @media (max-width: 768px)": {" nav button[webcompy-cid-xxx]": {"display": "block"}},
}
```

**Rationale:**

- At-rule syntax must remain valid
- Selectors inside at-rule blocks still receive cid (correct behavior)
- Simple and predictable

### Decision 3: Handle leading/trailing whitespace

**Approach:**

Use `strip()` for classification, but preserve original key:

```python
stripped_selector = selector.strip()
if _classify_nested_key(stripped_selector) == "at-rule":
    processed_selector = selector  # Preserve original (with spaces if present)
```

**Rationale:**

- `" @media (...)"` should be classified as at-rule despite leading space
- Preserve developer's original formatting
- CSS output will have consistent spacing from `_generate_css_recursive`

**Alternatives Considered:**

- **Always strip**: Could change intended formatting
- **Require exact syntax**: Too strict, developers may add spaces

### Decision 4: No changes to `_generate_css_recursive`

**Approach:**

The existing `_generate_css_recursive` function already handles at-rules correctly:

```python
if key_type == "at-rule":
    inner_css = _generate_css_recursive(selector, nested_styles)
    result += f"{nested_selector} {{ {inner_css} }}"
```

Since the setter now passes at-rule keys unchanged, this logic works as intended.

**Rationale:**

- Separation of concerns: setter handles cid, generator handles CSS structure
- Minimal changes reduce risk
- Existing tests for nested at-rules continue to pass

## Risks / Trade-offs

### Risk 1: Edge cases in at-rule detection

**Risk:** Non-standard at-rules or custom at-rules may not start with `@`.

**Mitigation:**

- CSS spec defines at-rules as `@`-prefixed
- Custom at-rules are not in scope (non-goal)
- Can extend detection later if needed

### Risk 2: Whitespace variations

**Risk:** Developers may use inconsistent whitespace (e.g., `"@media(...)"` vs `" @media (...)"`).

**Mitigation:**

- `strip()` handles leading/trailing spaces
- Classification uses stripped key
- CSS output is normalized by `_generate_css_recursive`

### Risk 3: Future nested at-rule support

**Risk:** If nested at-rules (at-rule inside at-rule) are added later, this change may need adjustment.

**Mitigation:**

- Current fix is orthogonal to nested at-rules
- Nested at-rules would require changes to `_generate_css_recursive`, not setter
- Document as non-goal for this change

## Migration Plan

**No migration required** — this is a bug fix, not a breaking change.

**Before (Invalid CSS):**

```css
@media[webcompy-cid-xxx] (max-width:[webcompy-cid-xxx] 768px)[webcompy-cid-xxx] nav button { display: block; }
```

**After (Valid CSS):**

```css
@media (max-width: 768px) { nav[webcompy-cid-xxx] button[webcompy-cid-xxx] { display: block; } }
```

**Steps:**

1. Update `scoped_style` setter to detect at-rules
2. Add unit tests for top-level at-rule
3. Add E2E test for top-level at-rule
4. Update specs with requirement
5. Run existing tests to verify no regressions

## Open Questions

None — implementation approach is clear and minimal.
