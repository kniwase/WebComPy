# Delta Spec: template-engine

## ADDED Requirements

### Requirement: Template engine shall validate colon-prefixed attributes on HTML elements

On HTML elements, the only recognized `:`-prefixed attribute SHALL be `:ref`. Any other `:`-prefixed attribute SHALL raise `WebComPyException` at bind time with a message naming the attribute and suggesting `{{ }}` interpolation as the alternative. The value resolved via `:ref` SHALL be a `DomNodeRef` instance; any other type SHALL raise `WebComPyException` at bind time naming the variable and its observed type.

#### Scenario: Non-ref colon attribute rejected
- **WHEN** the template contains `<div :class="cls">`
- **THEN** `WebComPyException` SHALL be raised at bind time
- **AND** the message SHALL name `:class` and suggest using `class="{{ cls }}"` interpolation

#### Scenario: Ref binding type validation
- **WHEN** `render_template('<input :ref="r">', {"r": "not-a-ref"})` is called
- **THEN** `WebComPyException` SHALL be raised at bind time naming `r` and its observed type (`str`)

#### Scenario: Component tags unaffected
- **WHEN** a `:`-prefixed attribute appears on a component tag (e.g., `<user-card :count="n">`)
- **THEN** it SHALL continue to be bound as a dynamic prop (no error)

### Requirement: Template engine shall reject malformed HTML with descriptive errors

Mismatched closing tags, unclosed elements at end of input, and stray closing tags SHALL raise `WebComPyException` instead of being silently recovered or ignored. Error messages SHALL name the offending tag and, for mismatches, the expected open tag.

#### Scenario: Mismatched closing tag
- **WHEN** the template contains `<div><b>bold</div></b>`
- **THEN** `WebComPyException` SHALL be raised with a message indicating `</div>` was encountered while `<b>` was open

#### Scenario: Unclosed element at EOF
- **WHEN** the template contains `<div><p>hi` with no closing tags
- **THEN** `WebComPyException` SHALL be raised listing the unclosed tag(s)

#### Scenario: Stray closing tag
- **WHEN** the template contains `<div>text</span></div>`
- **THEN** `WebComPyException` SHALL be raised naming the stray `</span>`

### Requirement: Template engine shall provide descriptive errors for unsupported expressions and invalid iterables

Template-originated binding failures SHALL raise `WebComPyException` (not raw `TypeError`/`KeyError`) with the offending variable or expression named. `{% if %}` conditions that are not resolvable variable paths SHALL produce an error stating that only variable paths (with dot notation) are supported. `{% for %}` targets that are not iterable SHALL produce an error naming the variable and its type. `{{ }}` spans matching brace syntax but not the identifier/dot-notation grammar SHALL raise `WebComPyException` in text content and directive positions.

#### Scenario: Unsupported if expression
- **WHEN** the template contains `{% if a > b %}` with `a` and `b` in the context
- **THEN** `WebComPyException` SHALL be raised stating that only variable paths are supported in `{% if %}` conditions, naming the expression `a > b`

#### Scenario: Non-iterable for target
- **WHEN** `{% for item in items %}` is used and `items` resolves to `None` or `5`
- **THEN** `WebComPyException` SHALL be raised naming `items` and its observed type

#### Scenario: Unsupported hole expression in text
- **WHEN** the template contains `<p>{{ items[0] }}</p>`
- **THEN** `WebComPyException` SHALL be raised stating that subscripts/calls/filters are not supported in `{{ }}` holes

### Requirement: Template engine shall reject event handler attributes with modifiers

`@event` attribute names containing a modifier suffix (e.g., `@click.stop`, `@keyup.enter`) SHALL raise `WebComPyException` at bind time instead of registering a never-firing event name. The message SHALL name the attribute and state that event modifiers are not supported.

#### Scenario: Modifier rejected
- **WHEN** the template contains `<button @click.stop="handler">`
- **THEN** `WebComPyException` SHALL be raised naming `@click.stop` and stating that modifiers are not supported

### Requirement: Template AST cache shall distinguish parse functions

The template AST cache key SHALL incorporate the identity of the parse function, so that a custom `parse_fn` and the default parser never share a cache entry for the same source string.

#### Scenario: Custom parse function does not collide with default
- **WHEN** `render_template` is called with source `S` using the default parser, then with source `S` using a custom `parse_fn`
- **THEN** the custom `parse_fn` SHALL be invoked (not served the default parser's cached AST)

### Requirement: Markdown code blocks and code spans shall be protected from template processing

Fenced code blocks and inline code spans produced by `DefaultMarkdownParser` SHALL NOT be subject to `{{ }}` interpolation or `{% %}` directive execution when the resulting HTML is bound by `render_template`. Template-syntax-looking text inside code SHALL be rendered literally.

#### Scenario: Hole inside fenced code block
- **WHEN** `render_markdown` is called with a fenced code block containing `{{ x }}` and context `{"x": "secret"}`
- **THEN** the rendered `<pre><code>` content SHALL contain the literal text `{{ x }}`
- **AND** the value `secret` SHALL NOT appear in the output

#### Scenario: Directive inside fenced code block
- **WHEN** a fenced code block contains `{% if y %}text{% endif %}`
- **THEN** the directive SHALL NOT be executed
- **AND** the `<pre><code>` element SHALL remain a single intact block containing the literal directive text

#### Scenario: Hole inside inline code span
- **WHEN** a paragraph contains `` `{{ x }}` `` as a code span
- **THEN** the `<code>` content SHALL be the literal text `{{ x }}`

### Requirement: Markdown inline tokenization shall be order-independent and spoof-resistant

Inline Markdown processing SHALL correctly nest previously-tokenized elements inside later-tokenized ones regardless of processing order (e.g., italic containing bold, strikethrough containing bold). Internal placeholder keys SHALL never appear in rendered output, and SHALL be constructed so user input cannot collide with or spoof them.

#### Scenario: Italic containing bold
- **WHEN** the source contains `*a **b** c*`
- **THEN** the output SHALL be `<em>a <strong>b</strong> c</em>`
- **AND** no placeholder text (e.g., `__WEBCOMPY_INLINE_`) SHALL appear in the output

#### Scenario: Strikethrough containing bold
- **WHEN** the source contains `~~a **b** c~~`
- **THEN** the output SHALL be `<del>a <strong>b</strong> c</del>`

#### Scenario: Placeholder spoofing impossible
- **WHEN** the source text contains a string resembling an internal placeholder key alongside real inline markup
- **THEN** the literal user text SHALL be preserved as-is
- **AND** only genuine markup SHALL be converted

### Requirement: Markdown links and images shall restrict URL schemes

`DefaultMarkdownParser` SHALL only emit `href`/`src` attributes for URLs with an allowed scheme: `http:`, `https:`, `mailto:`, relative URLs (no scheme), and fragment identifiers (`#...`). URLs with any other scheme (including `javascript:`, `data:`, `vbscript:`) SHALL NOT produce a link or image element; the link text SHALL be rendered as plain text instead.

#### Scenario: javascript URL neutralized
- **WHEN** the source contains `[click](javascript:alert(1))`
- **THEN** no `<a>` element with a `javascript:` href SHALL be emitted
- **AND** the text `click` SHALL be rendered as plain text

#### Scenario: Allowed schemes unaffected
- **WHEN** the source contains links with `https:`, `http:`, `mailto:`, relative (`/docs`, `./page.md`), and fragment (`#section`) URLs
- **THEN** all SHALL render as normal `<a href>` elements

### Requirement: Markdown list handling shall be consistent and lossless

The block parser SHALL recognize `+` as an unordered list marker (consistent with the for-body list detector). Multi-line list-item text SHALL be joined with a single space. Ordered lists SHALL preserve the first item's number via a `start` attribute when it differs from 1. Spaced horizontal-rule patterns (`* * *`, `- - -`, `_ _ _`) SHALL be recognized as `<hr>` before list or paragraph handling.

#### Scenario: Plus-marker list
- **WHEN** the source contains `+ one` and `+ two`
- **THEN** the output SHALL be `<ul><li>one</li><li>two</li></ul>`

#### Scenario: Plus-marker for-loop body
- **WHEN** `render_markdown` processes `{% for i in items %}` with body lines starting with `+ `
- **THEN** the merged output SHALL be a single `<ul>` with `<li>` children (not paragraphs)

#### Scenario: Multi-line list item
- **WHEN** the source contains `- foo` followed by an indented continuation line `  bar`
- **THEN** the output SHALL be `<li>foo bar</li>` (single-space joined)

#### Scenario: Ordered list start number
- **WHEN** the source contains `3. three` and `4. four`
- **THEN** the output SHALL be `<ol start="3"><li>three</li><li>four</li></ol>`

#### Scenario: Spaced horizontal rule
- **WHEN** the source contains `* * *` or `- - -` on its own line
- **THEN** the output SHALL be `<hr>` (not a `<ul>` or paragraph)

## MODIFIED Requirements

### Requirement: Template engine shall handle boolean attributes

Boolean HTML attributes (e.g., `disabled`, `checked`) that have no value SHALL be converted to `True` for the attribute dict. An attribute with an explicit empty-string value (`alt=""`) is NOT boolean and SHALL be preserved as the empty string `""`.

#### Scenario: Boolean attribute conversion
- **WHEN** the template contains `<input disabled>`
- **THEN** the attribute SHALL be `{"disabled": True}` (which `_proc_attr` converts to `""` in the DOM)

#### Scenario: Boolean attribute with explicit value
- **WHEN** the template contains `<input disabled="disabled">`
- **THEN** the attribute SHALL be `{"disabled": "disabled"}` (string value preserved)

#### Scenario: Empty-string attribute value is not boolean
- **WHEN** the template contains `<img alt="">`
- **THEN** the attribute SHALL be `{"alt": ""}` (empty string, not `True`)
