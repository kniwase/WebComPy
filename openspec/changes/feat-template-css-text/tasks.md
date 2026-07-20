## 1. CSS Parser Implementation

- [x] 1.1 Implement `parse_css(text: str) -> StyleDict` in `webcompy/template/_css_parser.py`
- [x] 1.2 Implement comment stripping: `re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)`
- [x] 1.3 Implement `read_key` with parenthesis-depth tracking for `(`, `)` to handle at-rule arguments
- [x] 1.4 Implement `read_braced` with brace-depth matching for `{`, `}` to extract nested blocks
- [x] 1.5 Implement `parse_block_content` distinguishing properties (delimited by `;`) from nested rules (delimited by `{}`)
- [x] 1.6 Implement `textwrap.dedent` application before parsing

## 2. CSS Template Functions

- [x] 2.1 Implement `css_text(source: str) -> dict[str, StyleDict]` in `webcompy/template/_css_template.py`
- [x] 2.2 Implement `css_text_template(source: str, context: dict) -> Callable[[], dict[str, StyleDict]]`
- [x] 2.3 Import `resolve_holes` from `webcompy.template._holes` (shared module created by Change 1)
- [x] 2.4 Correct `ReactiveScopedStyleFunc` type alias in `packages/webcompy/src/webcompy/components/_reactive_scoped_style.py:61` from `Callable[[], "StyleDict"]` to `Callable[[], "dict[str, StyleDict]"]` — matches the runtime contract of `render_css()` / `_apply_scope()` which iterate `.items()` over the factory return value; type-only change (no behavioral effect)

## 3. Public API

- [x] 3.1 Export `css_text`, `css_text_template` from `webcompy.template.__init__`

## 4. Unit Tests — CSS Parser

- [x] 4.1 Basic selectors (`.class`, `#id`, `element`, `*`)
- [x] 4.2 Combinator selectors (`.a > .b`, `.a + .b`, `.a ~ .b`, `.a .b`)
- [x] 4.3 Pseudo-classes (`:hover`, `:focus`, `:nth-child(n)`, `:not(sel)`)
- [x] 4.4 Pseudo-elements (`::before`, `::after`, `::placeholder`)
- [x] 4.5 At-rules (`@media`, `@supports`, `@container`)
- [x] 4.6 `@keyframes` with percentage selectors (`0%`, `100%`, `from`, `to`)
- [x] 4.7 Nested at-rules (at-rule inside at-rule)
- [x] 4.8 Mixed properties and nested rules in one block
- [x] 4.9 Comments (`/* ... */`) stripped correctly
- [x] 4.10 Multi-value properties (`font-family: a, b, c`)
- [x] 4.11 CSS variables (`--custom: value`) preserved as raw strings

## 5. Unit Tests — Template Functions

- [x] 5.1 `css_text` with plain CSS string returns correct `dict[str, StyleDict]`
- [x] 5.2 `css_text` composes with `await load_text(path)` for file-based CSS (async setup pattern; server records for hydration)
- [x] 5.3 `css_text_template` resolves `{{ }}` in CSS text
- [x] 5.4 `css_text_template` factory tracks Signal dependencies (Signal change → new `dict[str, StyleDict]`)
- [x] 5.5 `css_text_template` returns `Callable[[], dict[str, StyleDict]]` type compatible with `reactive_scoped_style`
- [x] 5.6 `textwrap.dedent` applied to CSS text

## 6. Integration Tests

- [x] 6.1 Component with `css_text()` static scoped_style
- [x] 6.2 Component with reactive CSS text (`css_text_template` + `reactive_scoped_style`)
- [x] 6.3 Reactive style updates `<style>` element on Signal change
- [x] 6.4 File-based CSS loading via `await load_text` + `css_text` composition (async component setup; SSR records resource for hydration, browser resolves from payload)
- [x] 6.5 Backward compat: dict `scoped_style` unchanged
- [x] 6.6 Backward compat: dict factory in `reactive_scoped_style` unchanged

## 7. CI Review Update

- [ ] 7.1 Update `.opencode/agents/ci-review.md`: add CSS text template patterns
- [ ] 7.2 Update `AGENTS.md` File→Spec Mapping: `webcompy/template/_css_parser.py` and `_css_template.py` → `template-engine` spec
