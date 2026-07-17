## Why

WebComPy currently requires developers to define scoped CSS as Python nested dictionaries (`".btn": {"color": "red"}`). This is verbose, unnatural for web developers who expect to write regular CSS, and prevents the use of standard CSS tooling. Adding CSS text support lets developers write CSS in its natural form, with Jinja2-style `{{ }}` interpolation for reactive styles that leverage WebComPy's existing scoped_style infrastructure.

## What Changes

- Add a CSS text parser (`css_text`) that converts CSS text strings into the `StyleDict` format used by WebComPy's scoped_style system
- Add `css_text_template(source, context)` that returns a factory function supporting `{{ varname }}` interpolation with reactive Signal tracking
- Support all CSS constructs handled by WebComPy's scoped_style: selectors, combinators, pseudo-classes/elements, at-rules (`@media`, `@supports`, `@container`, `@keyframes`), and nested rules
- Support file-based CSS loading via `Path`
- `css_text()` and `css_text_template()` provide an alternative CSS-text-based API for creating scoped styles from natural CSS syntax; the existing dict-based `scoped_style` API remains unchanged and fully supported
- Imports `resolve_holes` / `HOLE_PATTERN` from Change 1's shared `_holes.py` module
- No existing API changes — purely additive

## Capabilities

### New Capabilities
_None — extends `template-engine` and `reactive-scoped-style`_

### Modified Capabilities
- `template-engine`: CSS text parsing and `{{ }}` interpolation for scoped styles
- `reactive-scoped-style`: `reactive_scoped_style` can be used with `css_text_template` for reactive CSS text

## Known Issues Addressed
_None_

## Non-goals
- Direct string/Path assignment to `scoped_style` setter (must use `css_text()`)
- Modification of `ReactiveScopedStyle` or `ComponentGenerator` internals
- CSS validation/linting
- Sass/Less/CSS-in-JS
- `{{ }}` support in static scoped_style (no component context available at module level)

## Impact

- **New file**: `webcompy/template/_css_parser.py` — CSS text → StyleDict parser (~150 lines)
- **New file**: `webcompy/template/_css_template.py` — `css_text`, `css_text_template` functions
- **Shared dependency**: `webcompy/template/_holes.py` (created by Change 1 — `resolve_holes`, `HOLE_PATTERN`)
- **Type-level core correction (independent of CSS text)**: `_reactive_scoped_style.py` `ReactiveScopedStyleFunc` alias corrected from `Callable[[], StyleDict]` to `Callable[[], dict[str, StyleDict]]` — this is a pre-existing type imprecision fix that aligns the alias with the runtime contract of `render_css()` / `_apply_scope()`; included here because `css_text_template`'s return type becomes directly assignable to `ReactiveScopedStyleFunc` after this correction
- **No breaking changes**: Existing dict-based scoped_style API unchanged

## Dependencies

- **Depends on**: Change 1 (template interpolation — `_holes.py` shared module with `resolve_holes` / `HOLE_PATTERN`)
- **Depends on**: Change 4 (file loading — `_load_file` for `Path` support)
- **Required by**: None
- **Recommended implementation order**: Fifth template-engine change (0 → 1 → 2 → 3 → 4 → **5** → 6 → 7)
