# Syntax Highlighting Component

## Purpose

`SyntaxHighlighting` is a reusable component for displaying syntax-highlighted code via highlight.js. It accepts either a static string or a reactive `SignalBase[str]` for the code, applies lightweight input validation, and renders the code in a `<pre><code>` block using `hljs.highlight()` with `innerHTML` for safe, efficient DOM updates. It uses `:preserve_children` to prevent WebComPy's cleanup loop from destroying hljs-injected `<span>` elements.

## Requirements

### Requirement: SyntaxHighlighting shall accept both str and SignalBase[str] for code prop

The `code` prop SHALL accept either a plain `str` or a `SignalBase[str]`. When a `str` is provided, highlighting SHALL run once when the component is first rendered. When a `SignalBase[str]` is provided, highlighting SHALL run on first render and re-run whenever the signal value changes.

#### Scenario: Static string code
- **WHEN** `SyntaxHighlighting({"code": "print('hello')", "lang": "python"})` is rendered
- **THEN** the code SHALL be highlighted once on first render
- **AND** no `on_after_updating` callback SHALL be registered

#### Scenario: Reactive signal code
- **WHEN** `SyntaxHighlighting({"code": source_code_signal, "lang": "python"})` is rendered
- **AND** `source_code_signal.value` is later updated to a new string
- **THEN** the highlight SHALL re-run with the new code
- **AND** the DOM SHALL reflect the updated highlighted content

### Requirement: SyntaxHighlighting shall use hljs.highlight() with innerHTML

The component SHALL call `hljs.highlight(source, {"language": lang})` and set the result's `value` directly on the `<code>` element via `innerHTML`. It SHALL NOT call `hljs.highlightElement()`.

#### Scenario: hljs.highlight is used instead of highlightElement
- **WHEN** the component's highlight logic runs
- **THEN** `hljs.highlight(code, options)` SHALL be called with the source string and language
- **AND** `code_ref.element.innerHTML = result.value` SHALL be set with the returned HTML string
- **AND** `hljs.highlightElement()` SHALL NOT be called

#### Scenario: Highlight re-runs when signal changes
- **WHEN** the `code` prop is a `SignalBase[str]` with initial value `"x = 1"`
- **AND** the signal value is updated to `"x = 2"`
- **THEN** `hljs.highlight("x = 2", ...)` SHALL be called
- **AND** the `<code>` element's `innerHTML` SHALL be updated

### Requirement: SyntaxHighlighting shall validate code input

The component SHALL validate the code string before passing it to hljs. Validation SHALL include:
- Type check: non-string values SHALL result in an empty string
- Empty check: empty strings SHALL be returned as-is (no hljs call)
- Size limit: strings longer than 100,000 characters SHALL be replaced with an error message
- Null byte detection: strings containing `\x00` SHALL be replaced with an error message

The input SHALL NOT be HTML-escaped before passing to hljs, as that would interfere with hljs's tokenization.

#### Scenario: Normal code passes validation
- **WHEN** a valid Python source string of reasonable size is provided
- **THEN** the string SHALL be passed to `hljs.highlight()` unchanged

#### Scenario: Code exceeds size limit
- **WHEN** the code string exceeds 100,000 characters
- **THEN** the component SHALL display `[Error: code too large]` instead of calling hljs

#### Scenario: Code contains null bytes
- **WHEN** the code string contains `\x00` characters
- **THEN** the component SHALL display `[Error: invalid characters]` instead of calling hljs

#### Scenario: Empty code string
- **WHEN** the code string is empty (after stripping whitespace)
- **THEN** `hljs.highlight()` SHALL NOT be called
- **AND** the `<code>` element SHALL remain empty

### Requirement: SyntaxHighlighting shall use :preserve_children on the code element

The `<code>` element rendered by `SyntaxHighlighting` SHALL have `:preserve_children: True` and SHALL have no WebComPy-managed children (no `TextElement`). This prevents the framework's cleanup loop from removing hljs-injected `<span>` child nodes.

#### Scenario: Code element uses :preserve_children
- **WHEN** `SyntaxHighlighting` renders
- **THEN** the inner `<code>` element SHALL have `_preserve_children = True`
- **AND** the `<code>` element SHALL have `_children_length = 0`

#### Scenario: hljs spans survive re-render
- **WHEN** a `SyntaxHighlighting` with a `SignalBase[str]` prop is re-rendered
- **THEN** hljs-generated `<span>` child nodes of the `<code>` element SHALL NOT be removed by WebComPy's cleanup loop

### Requirement: DemoDisplay shall delegate to SyntaxHighlighting

`DemoDisplay` SHALL use `SyntaxHighlighting` for code rendering and SHALL NOT contain its own hljs logic. `DemoDisplay` SHALL pass its `source_code` Signal directly to `SyntaxHighlighting` as the `code` prop.

#### Scenario: DemoDisplay delegates code rendering
- **WHEN** `DemoDisplay` is rendered with async-loaded source code
- **THEN** the Code card SHALL contain a `SyntaxHighlighting` component instance
- **AND** `DemoDisplay` SHALL NOT have `code_ref`, `get_hljs`, or `run_highlight` local variables
- **AND** `DemoDisplay` SHALL NOT call `hljs.highlightElement()` or `hljs.highlight()`
