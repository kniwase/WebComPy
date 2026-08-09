# Delta: template-engine

## ADDED Requirements

### Requirement: render_markdown shall support opt-in heading id injection

`render_markdown` SHALL accept a keyword-only `heading_ids: bool = False` option. When `True`, every `<h1>`–`<h6>` element in the rendered tree SHALL receive an `id` attribute containing a slug derived from the heading's text content. When `False` (default), heading elements SHALL be rendered exactly as today, preserving cmark-gfm conformance of the default output.

Slugs SHALL be generated as follows: Unicode-aware lowercasing, runs of whitespace replaced with single `-` characters, all characters that are not alphanumeric or `-` removed. Duplicate slugs within one document SHALL receive `-2`, `-3`, … suffixes in document order. Slug generation SHALL be deterministic for identical input.

#### Scenario: Heading ids injected when enabled

- **WHEN** `render_markdown("# Getting Started", heading_ids=True)` is called
- **THEN** the rendered `<h1>` element has `id="getting-started"`

#### Scenario: Default behavior unchanged

- **WHEN** `render_markdown("# Getting Started")` is called without options
- **THEN** the rendered `<h1>` element has no `id` attribute

#### Scenario: Duplicate heading slugs are deduplicated

- **WHEN** a document contains two headings with the same text and `heading_ids=True`
- **THEN** the first heading receives the base slug and the second receives the slug with a `-2` suffix

#### Scenario: Non-ASCII heading text

- **WHEN** a heading contains CJK characters and `heading_ids=True`
- **THEN** the slug retains the alphanumeric CJK characters so the heading remains addressable

### Requirement: render_markdown shall support opt-in code block highlighting

`render_markdown` SHALL accept a keyword-only `code_blocks: bool = False` option. When `True`, every `<pre>` element whose sole significant child is a `<code class="language-{lang}">` element SHALL be replaced by a `CodeBlock` component receiving the literal code text and `lang`. When `False` (default), fenced code blocks SHALL render as plain `<pre><code>` exactly as today.

The extracted code content SHALL remain literal: it MUST NOT be subject to `{{ }}` interpolation or directive processing at any point.

#### Scenario: Fenced code replaced with CodeBlock

- **WHEN** `render_markdown` is called with `code_blocks=True` on a document containing a ` ```python ` fenced block
- **THEN** the output tree contains a `CodeBlock` element with `lang="python"` and the literal code text instead of a `<pre><code>` subtree

#### Scenario: Default behavior unchanged

- **WHEN** `render_markdown` is called without options on a document containing a fenced block
- **THEN** the output contains a plain `<pre><code class="language-python">` subtree

#### Scenario: Code content stays literal

- **WHEN** a fenced block contains text resembling template syntax (e.g. `{{ name }}`) and `code_blocks=True`
- **THEN** the `CodeBlock` receives the text verbatim with no interpolation attempted

### Requirement: render_markdown shall support opt-in class map injection

`render_markdown` SHALL accept a keyword-only `classes: Mapping[str, str] | None = None` option mapping tag names to CSS class strings. When provided, every rendered element whose tag name is a key of the mapping SHALL have the mapped classes merged into its `class` attribute. Classes SHALL be merged additively with any classes already present on the element. When `None` (default), no classes are injected.

#### Scenario: Classes injected for mapped tags

- **WHEN** `render_markdown(source, classes={"table": "doc-table"})` renders a GFM table
- **THEN** the `<table>` element's `class` attribute includes `doc-table`

#### Scenario: Merge with existing classes

- **WHEN** an element already carries a class (e.g. `<code class="language-python">`) and its tag is mapped
- **THEN** the resulting `class` attribute contains both the original and the mapped classes

#### Scenario: Default behavior unchanged

- **WHEN** `render_markdown` is called without `classes`
- **THEN** rendered elements carry only the classes emitted by the parser today
