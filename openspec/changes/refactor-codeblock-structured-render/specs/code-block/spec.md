# code-block — Structured CodeBlock Rendering Deltas

## MODIFIED Requirements

### Requirement: The framework SHALL provide a `CodeBlock` component

The framework SHALL provide a `webcompy.ui.code_block.CodeBlock` component that accepts `code: str | Signal[str]` and `lang: str` props and renders the code inside `<pre><code class="language-{lang}">...</code></pre>`, with the code tokenized into `<span class="...">` elements by the registered lexer for `lang`. Each token span SHALL be a framework-managed element rendered as a direct child of the `<code>` element: a `<span>` with class `tok-{type}` plus the Pygments short class when one exists, containing the token text as a text node. The component SHALL NOT render token content through `raw_html()` or any other HTML-string injection: no intermediate wrapper element SHALL exist between `<code>` and the token spans, and token text SHALL be assigned as text content so it is inherently escaped. When `code` is a static string, the spans SHALL be rendered directly. When `code` is a `Signal`, the spans SHALL be re-rendered from a reactive token list derived from the signal's current value. When the code is empty, the component SHALL render no token spans regardless of the language. When the language is unknown or tokenization produces no tokens (and the code is non-empty), the component SHALL render a single `<span class="tok-ident">` element containing the escaped code.

#### Scenario: Rendering a static code block

- **WHEN** a component template includes `CodeBlock({"code": "def foo(): pass", "lang": "python"})`
- **THEN** the rendered HTML SHALL contain `<pre><code class="language-python">`
- **AND** the `<code>` element's children SHALL be the token spans themselves (e.g., `<span class="tok-kw k">def</span>` and similar), with no wrapper element in between
- **AND** the rendered HTML SHALL be identical between SSR and CSR

#### Scenario: Rendering a dynamic code block

- **WHEN** `CodeBlock` receives `code: Signal[str]` and the signal's value is updated after initial render
- **THEN** the displayed highlighted content SHALL update to reflect the new value
- **AND** the update SHALL happen in pure Python (no client-side JavaScript required)
- **AND** the spans SHALL be re-rendered from a reactive list derived from the signal's value

#### Scenario: Unknown language falls back to a single tok-ident span

- **WHEN** `CodeBlock` receives `lang: "nonexistent-language"` and a non-empty `code`
- **THEN** the `<code>` element SHALL contain a single direct child `<span class="tok-ident">` with the escaped code as its text content
- **AND** the component SHALL NOT raise `LexerNotFoundError`
- **AND** the same fallback SHALL apply when a registered lexer returns no tokens for the given code

#### Scenario: Empty code renders no token spans

- **WHEN** `CodeBlock` receives an empty `code` string
- **THEN** the `<code>` element SHALL have no children
- **AND** this SHALL hold even when the language is unknown

#### Scenario: Hydration adopts prerendered token spans

- **WHEN** a server-rendered code block is hydrated in the browser
- **AND** the client-side tokenization matches the prerendered content
- **THEN** the prerendered token span nodes SHALL be adopted (neither removed nor recreated)
- **AND** their text SHALL NOT be rewritten when it already matches
