# Spec Delta

## ADDED Requirements

### Requirement: CodeBlock SHALL support an opt-in copy-to-clipboard action

`webcompy.ui.code_block.CodeBlock` SHALL accept an optional `copyable: bool = False` prop. When `copyable` is `False` (default), the component SHALL preserve its existing `<pre><code class="language-{lang}">...</code></pre>` DOM output unchanged. When `copyable` is `True`, the component SHALL render a wrapper containing an accessible copy button (`type="button"`, descriptive `aria-label`) alongside the `<pre><code class="language-{lang}">...</code></pre>` block; activating the button in the browser SHALL copy the raw `code` string via `navigator.clipboard` and provide brief visual/accessible feedback (`Copied`), while keeping `<span class="tok-*">` elements as direct children of `<code>`.

#### Scenario: Default CodeBlock omits copy chrome

- **WHEN** `CodeBlock({"code": "x = 1", "lang": "python"})` renders without `copyable=True`
- **THEN** no copy button is rendered and existing SSR/CSR markup expectations remain unchanged

#### Scenario: Copyable CodeBlock renders button and preserves direct token spans

- **WHEN** `CodeBlock({"code": "x = 1", "lang": "python", "copyable": True})` renders
- **THEN** an accessible copy button is rendered outside `<pre>` and clicking it copies `"x = 1"` while displaying copied feedback
- **AND** `<code>` still contains direct `<span class="tok-*">` children with no intermediate wrapper inside `<code>`
