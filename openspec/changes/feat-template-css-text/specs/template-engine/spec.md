## ADDED Requirements

### Requirement: CSS text shall be parsed into scoped style dict structure

The framework SHALL provide a `css_text(source: str | Path) -> dict[str, StyleDict]` function that parses CSS text strings into the existing `StyleDict` (nested dict) format. The parser SHALL handle all CSS constructs supported by WebComPy's scoped_style system, including selectors, combinator selectors, pseudo-classes/elements, at-rules (`@media`, `@supports`, `@container`, `@keyframes`), and nested rules. `textwrap.dedent` SHALL be applied to the source before parsing. The return type `dict[str, StyleDict]` matches the `scoped_style` setter type (`_generator.py:253`).

#### Scenario: Basic selectors and properties
- **WHEN** `css_text(".btn { color: red; }")` is called
- **THEN** it SHALL return `{".btn": {"color": "red"}}`

#### Scenario: Pseudo-class nesting
- **WHEN** `css_text(".btn:hover { background: blue; }")` is called
- **THEN** it SHALL return `{".btn:hover": {"background": "blue"}}`

#### Scenario: Nested pseudo-class (implicit nesting)
- **WHEN** `css_text(".btn { color: red; :hover { background: blue; } }")` is called
- **THEN** it SHALL return `{".btn": {"color": "red", ":hover": {"background": "blue"}}}`

#### Scenario: At-rule
- **WHEN** `css_text("@media (max-width: 768px) { .btn { font-size: 12px; } }")` is called
- **THEN** it SHALL return `{"@media (max-width: 768px)": {".btn": {"font-size": "12px"}}}`

#### Scenario: @keyframes
- **WHEN** `css_text("@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }")` is called
- **THEN** it SHALL return `{"@keyframes spin": {"0%": {"transform": "rotate(0deg)"}, "100%": {"transform": "rotate(360deg)"}}}`

#### Scenario: Nested at-rules
- **WHEN** `css_text("@media (max-width: 768px) { @supports (display: grid) { .btn { display: grid; } } }")` is called
- **THEN** nested at-rules SHALL be parsed into nested dict structure

#### Scenario: Combinator selectors
- **WHEN** `css_text(".a > .b { color: red; }")` is called
- **THEN** it SHALL return `{".a > .b": {"color": "red"}}`

#### Scenario: CSS comments stripped
- **WHEN** `css_text("/* comment */ .btn { color: red; }")` is called
- **THEN** comments SHALL be stripped and the result SHALL be `{".btn": {"color": "red"}}`

#### Scenario: At-rule with paren-contained colon
- **WHEN** `@media (max-width: 768px)` contains `:` inside parentheses
- **THEN** the parser SHALL NOT treat the internal `:` as a property separator

#### Scenario: File loading
- **WHEN** `css_text(Path("styles/button.css"))` is called in a server environment
- **THEN** the file SHALL be read and its content parsed as CSS text

#### Scenario: File loading rejected in browser
- **WHEN** `css_text(Path("styles/button.css"))` is called in a PyScript browser environment
- **THEN** `WebComPyException` SHALL be raised with a message recommending inline CSS strings (inherited from Change 4's `_load_file`)

### Requirement: CSS text templates shall support {{ }} variable interpolation

The framework SHALL provide a `css_text_template(source: str | Path, context: dict) -> Callable[[], dict[str, StyleDict]]` function. The returned factory SHALL resolve `{{ varname }}` holes from the context using `resolve_holes` (from `_holes.py`), parse the resolved CSS text to `dict[str, StyleDict]`, and be suitable for use with `reactive_scoped_style`. `ReactiveScopedStyleFunc` (`_reactive_scoped_style.py:61`) SHALL be corrected from `Callable[[], StyleDict]` to `Callable[[], dict[str, StyleDict]]` so that `css_text_template`'s return type is directly assignable. This aligns the alias with the runtime contract of `render_css()` / `_apply_scope()` which iterate `.items()` over the factory return value (selector-keyed top-level dict).

#### Scenario: Factory resolves {{ }} before parsing
- **WHEN** `css_text_template(".btn { color: {{ color }}; }", {"color": Signal("blue")})` returns a factory
- **AND** the factory is called
- **THEN** `{{ color }}` SHALL be resolved to `"blue"` by reading `color.value`
- **AND** the result SHALL be `{".btn": {"color": "blue"}}`

#### Scenario: Signal dependency tracking in factory
- **WHEN** the returned factory is wrapped in `reactive_scoped_style` (creating a `Computed`)
- **AND** a referenced Signal changes
- **THEN** the `Computed` SHALL re-evaluate the factory, re-resolve `{{ }}`, and re-parse CSS
- **AND** the `<style>` element SHALL update reactively

#### Scenario: Factory with file source
- **WHEN** `css_text_template(Path("styles/dynamic.css"), context)` returns a factory
- **THEN** each factory call SHALL read the file, resolve `{{ }}`, and parse CSS

### Requirement: css_text and css_text_template shall be exported from webcompy.template

Both `css_text` and `css_text_template` SHALL be importable from `webcompy.template`.

#### Scenario: Import
- **WHEN** a developer writes `from webcompy.template import css_text, css_text_template`
- **THEN** both functions SHALL be available
