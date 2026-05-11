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

- Detect at-rule keys in `scoped_style` setter and skip cid application
- Generate valid CSS with wrapping `{ }` braces for top-level at-rules
- Support nested at-rules (at-rule inside at-rule) with recursive wrapping
- Support `@keyframes` with from/to/percentage inner keys (no cid applied)
- Scope pseudo-class/element selectors inside at-rules with `*[webcompy-cid-xxx]`
- Scope combinator selectors inside at-rules without orphan attribute selectors
- Apply cid to bare selectors inside at-rule blocks
- Maintain backward compatibility with existing nested and flat style usage
- Add unit tests for top-level at-rules
- Update specs with requirement

**Non-Goals:**

- `@font-face`, `@property`, `@counter-style` property at-rules (proceed as normal selectors — no special handling needed since they contain only CSS properties)
- Custom/non-standard at-rules
- Full CSS parsing beyond prefix detection combined with combinator pattern matching
- Performance optimizations (caching generated CSS)

## Decisions

### Decision 1: Use `_classify_nested_key` for at-rule detection in setter and getter

The setter strips the selector, classifies it with `_classify_nested_key`, and skips cid application for at-rules. Non-at-rule selectors receive cid as before via `_combinator_pattern.split/join`.

The getter dispatches top-level selectors based on classification:
- `@keyframes` → special handling (no cid on inner keys)
- Other at-rules (`@media`, `@supports`, `@container`) → recursive inner processing
- Regular selectors → existing `_generate_css_recursive` path (no cid parameter)

### Decision 2: Strip whitespace from all keys in setter

Both at-rule and non-at-rule keys are stripped before processing. This avoids orphan attribute selectors from leading whitespace in combinator selectors, and ensures clean at-rule declarations.

### Decision 3: `_scope_combinator_selector` helper for consistent scoping

A shared helper function replaces inline combinator scoping logic used in multiple places (getter, `_process_at_rule_inner`, `_generate_css_recursive`).

```python
def _scope_combinator_selector(selector: str, cid: str) -> str:
    parts = _combinator_pattern.split(selector)
    combinators = [*_combinator_pattern.findall(selector), ""]
    scoped_parts: list[str] = []
    for i, (s, c) in enumerate(zip(parts, combinators, strict=True)):
        if not s and i == 0:
            scoped_parts.append(f"*[webcompy-cid-{cid}]{c}")  # pseudo-scope combinator-first
        elif s:
            scoped_parts.append(f"{s}[webcompy-cid-{cid}]{c}")
        else:
            scoped_parts.append(c)
    return "".join(scoped_parts)
```

Key behaviors:
- Combinator-first selectors (`"> li"`) get `*[webcompy-cid-xxx]` prepended for scoping
- Empty string parts from the split do NOT get cid appended (prevents orphan attribute selectors)
- Regular parts get `[webcompy-cid-xxx]` appended between the selector and the combinator

### Decision 4: `_process_at_rule_inner` for recursive nested at-rule handling

A recursive method on `ComponentGenerator` processes inner selectors within at-rule blocks. It classifies each inner selector and handles:

- **at-rule** → recursive call to `_process_at_rule_inner`, wraps result in `{ }` (allows arbitrary nesting depth)
- **pseudo-class/element** → scoped with `*[webcompy-cid-{cid}]` prefix (e.g., `*[webcompy-cid-xxx]:hover`)
- **combinator** → scoped via `_scope_combinator_selector`
- **bare selector** → simple `selector[webcompy-cid-xxx]` appending

### Decision 5: `@keyframes` special handling in getter

`@keyframes` inner keys (`from`, `to`, `0%`, `100%`) are not CSS selectors and must not receive cid attributes. The getter detects `@keyframes` (before the general at-rule check) and passes inner keys through `_generate_css_recursive` without any cid scoping.

```css
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
```

This also applies when `@keyframes` is nested inside another at-rule (e.g., `@media`), where both the getter and `_process_at_rule_inner` detect the `@keyframes` prefix.

### Decision 6: Getter flow — top-level selector dispatch

```python
for selector, style_dict in self._style.items():
    stripped = selector.strip()
    if stripped.startswith("@keyframes"):
        # @keyframes: no cid on inner keys
        ...
    elif _classify_nested_key(stripped) == "at-rule":
        # @media, @supports, etc.: recursive inner processing
        ...
    else:
        # Regular selector: existing _generate_css_recursive (no cid)
        ...
```

### Decision 7: `_generate_css_recursive`'s `cid` parameter — defensive guard

The `cid` parameter is optional (`None` by default). When provided and the nested selector is a combinator, `_scope_combinator_selector` is used (with the `if not s and i == 0` guard preventing orphan attributes). The parameter is only passed when explicitly needed (inside at-rule blocks), keeping the non-at-rule path unchanged.

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

**No migration required** — this is a bug fix and feature extension, not a breaking change.

**Before (Invalid CSS for top-level at-rules):**

```css
@media[webcompy-cid-xxx] (max-width:[webcompy-cid-xxx] 768px) nav button { display: block; }
```

**After (Fully valid CSS with nesting and scoping):**

```css
/* Top-level at-rule */
@media (max-width: 768px) { .btn[webcompy-cid-xxx] { color: red; } }

/* Nested at-rules */
@media (max-width: 768px) { @supports (display: grid) { .card[webcompy-cid-xxx] { display: grid; } } }

/* @keyframes */
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

/* Pseudo-class inside at-rule */
@media (...) { *[webcompy-cid-xxx]:hover { background: yellow; } }

/* Combinator inside at-rule */
@media (...) { .menu[webcompy-cid-xxx] > li[webcompy-cid-xxx] { color: blue; } }
```

**Steps:**

1. Update `scoped_style` setter to detect at-rules and preserve them
2. Update `scoped_style` getter to handle top-level at-rules with wrapping braces
3. Add `_process_at_rule_inner` for recursive nested at-rule handling
4. Add `_scope_combinator_selector` helper for consistent combinator scoping
5. Add `@keyframes` special handling (no cid on inner keys)
6. Fix `_generate_css_recursive` combinator branch defensive guard
7. Add unit tests for all patterns (top-level, nested, @keyframes, pseudo, combinator)
8. Add E2E test for top-level at-rule
9. Update specs with requirements
10. Run existing tests to verify no regressions

## Open Questions

None — implementation approach is clear and minimal.
