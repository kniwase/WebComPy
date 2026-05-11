## Why

The `scoped_style` setter in `ComponentGenerator` applies the `[webcompy-cid-{id}]` attribute selector to **all** top-level keys, including CSS at-rules like `@media`, `@supports`, and `@container`. This results in invalid CSS output where the at-rule syntax itself is corrupted.

**Example of the bug:**

```python
# Developer writes:
Component.scoped_style = {
    " @media (max-width: 768px)": {
        " nav button": {"display": "block"},
    },
}

# Currently generates (INVALID CSS):
@media[webcompy-cid-xxx] (max-width:[webcompy-cid-xxx] 768px)[webcompy-cid-xxx]  nav button { display: block; }

# Should generate (VALID CSS):
@media (max-width: 768px) { nav[webcompy-cid-xxx] button[webcompy-cid-xxx] { display: block; } }
```

The previous change (`2026-05-10-fix-scoped-style-css-output`) fixed the CSS output structure for **nested** at-rules, but did not address the case where at-rules are used as **top-level keys** in `scoped_style`.

## What Changes

- **Fixed**: `ComponentGenerator.scoped_style` setter to detect at-rule keys (starting with `@`) and skip cid attribute application
- **Fixed**: At-rule keys are preserved as-is, while nested selectors inside at-rules receive proper cid scoping
- **Modified**: `webcompy/components/_generator.py` — `scoped_style` setter logic
- **Added**: Unit tests for top-level at-rule support
- **Added**: E2E tests verifying top-level at-rule CSS output
- **Non-breaking**: Existing nested at-rule usage continues to work unchanged

## Capabilities

### New Capabilities

- `top-level-at-rule-support`: Developers can use at-rules (`@media`, `@supports`, `@container`, etc.) as top-level keys in `scoped_style` dictionaries, with proper CSS output and scoped selectors inside the at-rule blocks

### Modified Capabilities

- `components`: Update scoped CSS requirements to specify that at-rule keys must not receive cid attribute scoping

## Impact

- **Code Changes**: `webcompy/components/_generator.py` — `scoped_style` setter (lines 158-169)
- **Spec Changes**: `openspec/specs/components/spec.md` — Add requirement for at-rule key handling
- **Tests**: Add unit tests for top-level at-rule; enhance E2E tests
- **Backward Compatibility**: Fully backward compatible — existing nested at-rule usage unchanged
- **Breaking Change**: None — this fixes a bug, not a behavior change

## Known Issues Addressed

This change addresses a bug introduced in the nested scoped style feature (`2026-05-09-feat-nested-scoped-style`):

- **Bug**: Top-level at-rule keys receive cid attribute, corrupting CSS syntax
- **Impact**: Browsers ignore the malformed at-rules, breaking responsive styles
- **Root Cause**: `scoped_style` setter applies cid to all keys without distinguishing at-rules from selectors

## Non-goals

- **No changes to `_generate_css_recursive`**: The existing CSS generation logic already handles at-rules correctly when they reach it unchanged
- **No new at-rule types**: This fix applies to all `@`-prefixed at-rules generically
- **No nested at-rule support**: At-rules inside at-rules (e.g., `@media` inside `@supports`) remain unsupported
- **No CSS parsing**: The fix uses simple string prefix detection (`startswith("@")`), not full CSS parsing
