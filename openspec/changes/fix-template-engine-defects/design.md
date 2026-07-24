# Design: fix-template-engine-defects

## Context

The WebComPy template engine spans three subsystems that share regex-based, single-pass text processing:

1. **HTML templates** (`webcompy/template/_parser.py`, `_binder.py`, `_holes.py`, `_cache.py`, `__init__.py`) — stdlib `html.parser`-based parsing, `{{ }}`/`{% %}` directive binding.
2. **CSS** (`_css_parser.py`, `_css_template.py` + rendering in `components/_generator.py`, `components/_reactive_scoped_style.py`) — CSS text → `dict[str, StyleDict]`, then `[webcompy-cid-*]` scoping via a combinator regex.
3. **Markdown** (`_markdown_default.py`, `_markdown_for.py`) — regex-based block/inline parser feeding HTML into the template pipeline.

An execution-verified audit found defects concentrated at exactly the places where regexes meet context-sensitive syntax (strings, brackets, nesting, token ordering). The defects fail silently in most cases, so users ship broken output without noticing.

## Goals / Non-Goals

**Goals:**
- Eliminate every confirmed crash (`@font-face` → `AttributeError`, `:`-attr mis-binding → `AttributeError`).
- Eliminate silent output corruption (invalid scoped selectors, leaked inline tokens, code-block template execution, corrupted attribute selectors/strings).
- Fail loudly with `WebComPyException` on unsupported constructs (event modifiers, `&` nesting, malformed HTML, unsupported expressions).
- Keep the current architecture (stdlib `html.parser`, dict-based StyleDict, regex-assisted Markdown) — this is defect repair, not a rewrite.

**Non-Goals:**
- CommonMark conformance or a multi-stage Markdown parser (future `refactor-markdown-parser`).
- New expression language features (comparisons, filters, subscripts).
- Documentation-only limitation write-ups (future `docs-template-limitations`).
- Performance optimization beyond what the fixes naturally provide.

## Decisions

### D1. Shared depth-aware CSS selector tokenizer

Introduce a single private helper (e.g. `_split_selector_parts(selector) -> tuple[list[str], list[str]]`) in `components/_css_utils.py` (new module) that walks the selector character-by-character tracking `( )` depth, `[ ]` depth, and string state (`"..."`/`'...'` with backslash escapes), splitting only on top-level combinators (`,`, `>`, `+`, `~`, whitespace runs).

- **Why**: The root cause of the four worst CSS scoping bugs (`:nth-child(2n+1)`, attribute values, `a~b`, newline combinators) is one regex (`_generator.py:20`) that cannot see nesting. Both the static setter and the reactive renderer consume it.
- **Alternative considered**: Extend the regex with lookarounds — rejected; regexes cannot match balanced nesting/strings robustly.
- **Unification**: The `scoped_style` setter and `_reactive_scoped_style` both call the same scoping function, ending the static/reactive divergence.

### D2. Pseudo-element-aware cid insertion

When appending `[webcompy-cid-N]` to a compound selector, insert it **before** any trailing `::pseudo-element` (and its functional arguments, e.g. `::slotted(...)`) instead of at the end.

- **Why**: CSS grammar requires pseudo-elements last; `.x::before[cid]` is invalid and the whole rule is dropped by browsers. Every `::before`/`::after` scoped style in the wild is currently dead.
- **Alternative considered**: Wrapping via `:where()` — rejected; changes specificity semantics.

### D3. Declaration-body at-rule classification

Classify at-rules by body shape: `@font-face`, `@page`, `@property`, `@counter-style` (declaration bodies, values are strings) are rendered **unscoped** like `@keyframes`; rule bodies (`@media`, `@supports`, `@container`, `@layer`) recurse with scoping. Keyframes matching becomes case-insensitive and vendor-prefix aware (`@(-webkit-|-moz-|-o-)?keyframes`).

- **Why**: The renderer assumes every at-rule value is a nested dict, so declaration bodies crash with `AttributeError`. These at-rules define global resources; scoping them is meaningless anyway.

### D4. CSS parser string/bracket state machine

Upgrade `_css_parser.py` internals (`_read_key`, `_read_braced`, comment stripping) to track `[ ]` depth and string literal state so structural characters (`;{}`, `/* */`) inside strings and attribute selectors are inert.

- **Why**: `[data-x="a;b"]` corrupts the parse, `content: "/* x */"` is destroyed by comment stripping, and `content: "{"` raises a misleading "unbalanced braces" error on valid CSS.
- **Alternative considered**: Documenting the limitation — rejected for `;` in strings and attribute selectors, which are realistic in the advertised `css_text(load_text(...))` file workflow.

### D5. Strict `:`-attribute and `:ref` validation

In `_binder.classify_attrs`, only `:ref` is recognized among `:`-prefixed attributes on HTML elements; anything else raises `WebComPyException` naming the attribute and suggesting `class="{{ ... }}"` interpolation. `:ref` values must be `DomNodeRef` instances or a `WebComPyException` is raised at bind time.

- **Why**: Today any `:attr` silently becomes `ref`, and a non-`DomNodeRef` crashes at render time with a confusing `AttributeError`.
- **Alternative considered**: Implementing Vue-style `:prop` dynamic binding — out of scope (new capability, not a defect fix).

### D6. Strict malformed-HTML errors

`handle_endtag` raises `WebComPyException` when the closing tag does not match the stack top (message includes expected vs actual tag and suggests checking nesting); EOF with a non-empty stack raises listing the unclosed tags.

- **Why**: Silent recovery currently nests trailing content into the wrong element, producing a subtly wrong tree that renders without complaint.
- **Trade-off accepted**: `render_markdown` output must therefore always be well-formed; the Markdown parser emits only balanced tags, so this holds. HTML-block passthrough lines are single-line or explicitly closed multi-line blocks, also balanced.

### D7. Directive-paragraph stripping tightened to spec

Replace the regex in `template/__init__.py` with one that matches `<p>` containing **exactly one** `{% %}` directive and nothing else (`<p>\s*(\{%\s*(?:if|elif|else|endif|for|endfor)\b[^%]*?%\})\s*</p>`), aligning with the existing spec scenario "if with text preserved".

- **Why**: Current `[^<]*?` also matches sibling text, stripping `<p>` wrappers the spec says must be preserved, changing rendered DOM.

### D8. Markdown code-block template protection

In `_markdown_default.py`, fenced code blocks and inline code spans escape `{{`/`{%` (e.g. to HTML entities or a protected placeholder) **before** the HTML is handed to `render_template`, so template syntax inside code is displayed literally.

- **Why**: Code examples containing `{{ config.secret }}` currently interpolate real context values (data leakage) and `{% if %}` inside code executes directives, corrupting the `<pre>` block.
- **Implementation note**: The `render_markdown` pipeline (`template/__init__.py`) must pass a flag or use placeholder tokens so `render_template`'s hole detection skips protected spans; placeholders are restored to literal `{{`/`{%` text nodes during binding.

### D9. Markdown inline tokenization made order-independent

Inline processing adopts per-token unique keys with a random/UUID-derived prefix (e.g. `\x00WC{n}\x00` or keyed by a per-render nonce) and resolves placeholders **recursively after each substitution pass** (or substitutes in reverse nesting order), so `*a **b** c*` and `~~a **b** c~~` nest correctly in either direction. NUL-containing keys also make user-input spoofing impossible.

### D10. URL scheme allow-list for Markdown links/images

`DefaultMarkdownParser` validates `href`/`src` against an allow-list: `http:`, `https:`, `mailto:`, relative URLs (no scheme), and fragment `#...`. Disallowed schemes (e.g. `javascript:`, `data:`, `vbscript:`) render the link text as plain text without an `<a>`/`<img>` wrapper.

- **Why**: `javascript:` URLs currently pass through verbatim (XSS for untrusted Markdown).
- **Trade-off accepted**: `data:` images are a legitimate use but are grouped with unsafe schemes; can be revisited when a sanitization option is designed.

### D11. Error-quality normalization

All template-originated failures become `WebComPyException` with the offending variable/attribute/tag name: non-iterable `{% for %}` targets, unsupported `{% if %}` expressions, unmatched `{% endif %}`/`{% endfor %}` (message clarified that directives cannot cross element boundaries), and `{{ }}` expressions that don't match the identifier/dot pattern (raised as errors in text positions rather than silently emitted — attribute positions keep literal behavior where patterns legitimately contain braces in prose... see Open Questions).

- **Why**: Silent literal output for `{{ items[0] }}` is a debugging trap.

### D12. Minor correctness fixes (no design controversy)

- Boolean attribute only when `value is None` (`alt=""` stays `""`).
- `+` added to the Markdown `_LIST_RE` marker set (aligning with `_markdown_for.py`).
- Multi-line list-item text joined with a single space.
- Ordered lists capture the first item's number → `<ol start="N">` (only emitted when N != 1).
- Spaced HR patterns (`* * *`, `- - -`, `_ _ _`) recognized before list/paragraph handling.
- Template AST cache key includes the parse function identity.

## Risks / Trade-offs

- [D6 strict HTML errors break existing sloppy templates] → All such templates currently render wrong trees; the error surfaces a real bug. Mitigation: clear messages with tag names; docs_app templates verified during implementation via `webcompy generate`.
- [D8 placeholder mechanism leaks into user-visible text if binding misses a restore] → Covered by tests asserting literal `{{ }}` rendering inside code blocks/spans across text and attribute positions.
- [D10 breaks `data:` image users] → Documented in the spec scenario; allow-list is a single constant easy to extend later.
- [D1 tokenizer adds a new module] → Scoped to pure functions, no state, no globals; keeps "No New Globals" invariant.
- [Reactive-scoped-style factory re-parse cost unchanged, but the shared helper must stay allocation-light] → Tokenizer is a single pass; no regex backtracking; acceptable.

## Migration Plan

Pure bug-fix change; no user migration required. Breaking items (D5, D6, event modifiers, `&` rejection) convert silent misbehavior into loud errors — users hitting them were already broken. docs_app is regenerated (`webcompy generate`) during implementation to prove no internal template relies on the old behavior.

## Open Questions

1. **D11 scope in attribute positions**: Should unsupported `{{ }}` expressions raise everywhere, or only in text/directive positions? Attribute values like `title="Cost: {{ a }} + {{ b }}"` are legitimate; the current plan raises only when a `{{ ... }}` span matches brace syntax but not the identifier/dot grammar. Final call during implementation of the error requirement.
2. **`@keyframes` name scoping**: Keyframe names remain global (collision-prone). Renaming/rewriting `animation` references is a feature, not a defect fix — confirmed out of scope here.
