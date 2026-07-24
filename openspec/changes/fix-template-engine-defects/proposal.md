# Proposal: fix-template-engine-defects

## Why

A systematic audit of the template engine (HTML templates, `css_text`/scoped-CSS pipeline, and the built-in Markdown parser) uncovered numerous defects that silently produce broken output or crash at runtime: `::before`/`::after` scoped styles are emitted as invalid CSS and dropped by browsers, `:nth-child(2n+1)` and attribute selectors are corrupted during scoping, `@font-face`/`@page` crash with a bare `AttributeError`, `:class`-style attributes are mis-bound as refs and crash rendering, nested inline Markdown leaks internal token keys (`__WEBCOMPY_INLINE_0__`) into the page, code blocks execute `{{ }}`/`{% %}` template syntax, and `javascript:` URLs pass through unsanitized. These are not edge cases — several fire on common, documented usage patterns and fail silently, making them hard for users to detect.

## What Changes

### HTML template parsing & binding

- **BREAKING** Reject `:`-prefixed attributes other than `:ref` on HTML elements with a `WebComPyException` at bind time (previously mis-bound as `ref`, crashing at render time); validate that `:ref` values are `DomNodeRef` instances.
- Fix the Markdown-pipeline directive-paragraph stripping to comply with the spec: `<p>` wrappers are removed only when the paragraph contains nothing but a single `{% %}` directive (sibling text preserves the `<p>`).
- **BREAKING** Raise `WebComPyException` on mismatched/unclosed/stray closing tags instead of silently producing a wrong tree.
- Distinguish empty-string attribute values (`alt=""` → `""`) from boolean attributes (`disabled` → `True`).
- Raise descriptive `WebComPyException` (with variable names) for non-iterable `{% for %}` targets and unsupported expressions (`{% if a > b %}`, `{{ items[0] }}`) instead of raw `TypeError`/`KeyError` or silent literal output.
- **BREAKING** Reject event-handler attributes with modifiers (`@click.stop`, `@keyup.enter`) instead of silently registering a never-firing event name.
- Include the parse function identity in the template AST cache key.

### CSS parsing & scoped-style rendering

- Replace the regex-based combinator splitter with a depth-aware tokenizer so scoping never splits inside `()`, `[]`, or string literals (fixes `:nth-child(2n+1)`, attribute values, escaped selectors).
- Insert the `[webcompy-cid-*]` attribute selector before trailing pseudo-elements (`.x[cid]::before`) instead of appending it after them.
- Unify static `scoped_style` setter and reactive scoping behind one shared helper (fixes `a~b`, top-level leading combinators, newline/tab descendant combinators, and the static-vs-reactive divergence).
- Render declaration-body at-rules (`@font-face`, `@page`, `@property`, `@counter-style`) unscoped instead of crashing with `AttributeError`; recognize vendor-prefixed/uppercase `@keyframes`.
- Add string/bracket awareness to the CSS parser: structural characters (`;{}`) inside strings and attribute selectors no longer corrupt parsing, and comment stripping respects string literals.
- **BREAKING** Reject CSS-nesting `&` selectors with a clear error instead of rendering them with wrong semantics.

### Markdown

- Protect fenced code blocks and code spans from `{{ }}` interpolation and `{% %}` directive execution (literal display, no value leakage).
- Fix the inline tokenization order bug that leaks `__WEBCOMPY_INLINE_N__` placeholders into output (`*a **b** c*`), and switch to spoof-resistant token keys.
- Sanitize link/image URLs with an allow-list of schemes (`http`, `https`, `mailto`, relative); other schemes (notably `javascript:`) are rendered as plain text.
- Align list-marker handling between the block parser and the for-body detector (`+` markers).
- Join multi-line list-item text with a space; preserve ordered-list start numbers via `<ol start="N">`.
- Handle spaced horizontal rules (`* * *`, `- - -`) as `<hr>`.

### Non-goals

- CommonMark conformance redesign (setext headings, `~~~` fences, `***`, backslash escapes, reference links, tables, etc.) — deferred to a future `refactor-markdown-parser` change.
- Documentation of intentional limitations — deferred to a `docs-template-limitations` change (OpenSpec-only PR).
- SSR/browser `html.parser` version-drift verification — separate investigation.
- No new template expression capabilities (comparisons, filters, subscripts remain unsupported; they only get better errors).

## Known Issues Addressed

- None of the cataloged known issues (signal system, component IDs, element system, router) are directly touched; this change addresses a newly discovered class of template-engine defects not yet in the known-issues list.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `template-engine`: New requirements for strict `:`-attribute validation, malformed-HTML errors, empty-string vs boolean attributes, expression/iterable error quality, event-modifier rejection, directive-paragraph stripping fix, code-block template protection, Markdown inline tokenization, URL scheme sanitization, list-marker/`<ol start>`/multi-line item fixes, and spaced horizontal rules.
- `reactive-scoped-style`: Scoping requirements corrected — depth-aware combinator tokenization, pseudo-element-aware cid insertion, declaration-body at-rules rendered unscoped, vendor-prefixed keyframes recognition.
- `components`: Static `scoped_style` scoping unified with the reactive path via a shared depth-aware helper; `&` nesting rejected.

## Impact

- **Code**: `packages/webcompy/src/webcompy/template/` (`_parser.py`, `_binder.py`, `_holes.py`, `_cache.py`, `__init__.py`, `_css_parser.py`, `_css_template.py`, `_markdown_default.py`, `_markdown_for.py`), `packages/webcompy/src/webcompy/components/_generator.py`, `packages/webcompy/src/webcompy/components/_reactive_scoped_style.py`.
- **Specs**: `template-engine`, `reactive-scoped-style`, `components`.
- **Tests**: `tests/test_template_parser.py`, `test_template_binder.py`, `test_template_markdown*.py`, `test_css_parser.py`, `test_css_template.py`, `test_scoped_css.py`, plus new cases for all fixed defects.
- **Breaking surface**: Templates relying on silent mis-binding of `:`-attributes, malformed HTML recovery, event modifiers, or `&` nesting will now fail loudly (all previously produced broken output anyway).
