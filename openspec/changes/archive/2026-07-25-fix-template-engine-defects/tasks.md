# Tasks: fix-template-engine-defects

## 1. CSS Scoping Tokenizer (shared foundation)

- [x] 1.1 Create `packages/webcompy/src/webcompy/components/_css_utils.py` with a depth-aware selector tokenizer `_split_selector_parts(selector)` tracking `()`/`[]`/string state (with backslash escapes), splitting on top-level combinators (`,`, `>`, `+`, `~`, whitespace runs incl. newlines/tabs)
- [x] 1.2 Add `_insert_cid(compound, cid)` helper that inserts `[webcompy-cid-{id}]` before any trailing pseudo-element chain (incl. functional pseudo-elements like `::slotted(...)`)
- [x] 1.3 Add shared `_scope_selector(selector, cid)` used for both flat and nested selectors; handle leading combinators by emitting `*[cid]` base
- [x] 1.4 Unit tests for tokenizer and cid insertion: `:nth-child(2n+1)`, `[data-x="a>b"]`, `[title="Hello, World"]`, `a~b`, `.a\n.b`, `.x::before`, `.x:hover::before`, escaped selectors (`.\31 23`), `:has(> img)`, leading `> .child`

## 2. CSS Scoping Integration

- [x] 2.1 Replace the `_combinator_pattern` regex path in `components/_generator.py` (setter + `_scope_combinator_selector` + `_generate_css_recursive` combinator branch) with the shared helpers from `_css_utils`
- [x] 2.2 Replace the reactive scoping path in `components/_reactive_scoped_style.py` with the same shared helpers (static/reactive divergence eliminated)
- [x] 2.3 Implement declaration-body at-rule classification (`@font-face`, `@page`, `@property`, `@counter-style` rendered unscoped, no crash) in both static and reactive renderers
- [x] 2.4 Make keyframes detection case-insensitive and vendor-prefix aware (`@(-webkit-|-moz-|-o-)?keyframes`) in both renderers
- [x] 2.5 Reject `&` nesting selectors with `WebComPyException` suggesting the nested dict form
- [x] 2.6 Tests: static vs reactive parity for identical inputs, declaration-body at-rules, vendor keyframes, `&` rejection, pseudo-element insertion end-to-end

## 3. CSS Parser String/Bracket Awareness

- [x] 3.1 Add string-literal and `[ ]` depth tracking to `_css_parser._read_key` so attribute selectors with `;`/`{`/`}` in values parse correctly
- [x] 3.2 Add string-literal tracking to `_read_braced`/`_parse_block_content` so `;{}` inside quoted strings are inert
- [x] 3.3 Make comment stripping string-aware (comments inside string literals are preserved)
- [x] 3.4 Tests: `[data-x="a;b"]`, `[data-x="a{b"]`, `content: "{"`/`";"`/`"}"`, `content: "/* not a comment */"`, unbalanced-brace error still fires for genuinely broken CSS

## 4. HTML Template Binding Validation

- [x] 4.1 In `_binder.classify_attrs`, restrict `:`-prefixed attributes on HTML elements to `:ref` only; raise `WebComPyException` for others (message suggests `{{ }}` interpolation); validate `:ref` values are `DomNodeRef`
- [x] 4.2 Reject `@event` attributes containing modifiers (e.g., `@click.stop`) with `WebComPyException`
- [x] 4.3 Empty-string attribute values bind as `""`, not `True` (`value is None` ⇒ boolean); update the `test_empty_value_boolean` test to the corrected behavior
- [x] 4.4 Raise `WebComPyException` for non-iterable `{% for %}` targets (name + type), unsupported `{% if %}` expressions, and `{{ }}` spans matching brace syntax but not the identifier/dot grammar (text/directive positions)
- [x] 4.5 Tests for all of the above incl. component-tag `:prop` path unaffected

## 5. HTML Parser Strictness & Cache

- [x] 5.1 `handle_endtag` raises `WebComPyException` on mismatched/stray closing tags (name expected vs actual); EOF with non-empty stack raises listing unclosed tags
- [x] 5.2 Include parse-function identity in the template AST cache key (`_cache.py`)
- [x] 5.3 Fix directive-paragraph stripping in `template/__init__.py` to only unwrap `<p>` containing exactly one `{% %}` directive and nothing else (spec compliance; add the missing "if with text preserved" test)
- [x] 5.4 Tests: malformed HTML errors, cache parse_fn isolation, `<p>{% if x %}text{% endif %}</p>` preserved, `render_markdown` output unaffected (well-formed)

## 6. Markdown Parser Defects

- [x] 6.1 Protect fenced code blocks and inline code spans from `{{ }}` interpolation and `{% %}` execution (placeholder mechanism restored to literal text during binding); tests assert literal `{{ x }}`/`{% if %}` rendering and no context-value leakage
- [x] 6.2 Make inline tokenization order-independent with spoof-resistant placeholder keys (NUL-prefixed, per-render nonce); resolve nested placeholders recursively
- [x] 6.3 Add URL scheme allow-list (`http:`, `https:`, `mailto:`, relative, `#fragment`) for links/images; disallowed schemes render link text as plain text
- [x] 6.4 Add `+` to `_LIST_RE`; join multi-line list-item text with a space; emit `<ol start="N">` when N != 1; recognize spaced HR patterns (`* * *`, `- - -`, `_ _ _`) before list/paragraph handling
- [x] 6.5 Tests for all of the above incl. `*a **b** c*`, `~~a **b** c~~`, placeholder spoofing, `javascript:` URLs, `+` for-loop bodies via `MarkdownForElement`

## 7. Verification & Regression Sweep

- [x] 7.1 `uv run ruff check .` and `uv run ruff format .` clean
- [x] 7.2 `uv run pyright` clean
- [x] 7.3 `uv run python -m pytest tests/ --tb=short` green (incl. updated/new tests)
- [x] 7.4 `uv run python -m webcompy generate` on docs_app succeeds — proves no internal template relies on old lenient behavior
- [x] 7.5 Update `.opencode/agents/ci-review.md` invariants if the change introduces new rules (e.g., strict-HTML, scoping tokenizer contract)
- [x] 7.6 Run E2E suite `scripts/run-e2e-tests.sh` (or relevant groups) to confirm no browser regressions
