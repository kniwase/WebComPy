# Delta Spec: template-engine

## MODIFIED Requirements

### Requirement: DefaultMarkdownParser shall convert Markdown to HTML

`DefaultMarkdownParser.render(source)` SHALL convert Markdown text to HTML strings using a two-phase CommonMark block parser (container stack + leaf blocks) as specified in the CommonMark appendix, extended with GFM tables and task list items. `textwrap.dedent` SHALL be applied to the source before parsing. Tabs SHALL be handled per CommonMark (advance to the next 4-column stop, with partial-tab support); no global tab-to-spaces normalization SHALL be performed, and tab characters inside code blocks SHALL be preserved per spec expansion rules.

#### Scenario: ATX headings
- **WHEN** source contains `# Title` through `###### Sub`
- **THEN** the output SHALL be `<h1>Title</h1>` through `<h6>Sub</h6>`
- **AND** closing hash sequences preceded by a space (`## Title ##`) SHALL be stripped
- **AND** `#hashtag` (no space after `#`) SHALL NOT be a heading (CommonMark requires a space)

#### Scenario: Setext headings
- **WHEN** source contains `Title` followed by an underline of `=` characters
- **THEN** the output SHALL be `<h1>Title</h1>`
- **AND** an underline of `-` characters SHALL produce `<h2>Title</h2>` (not a thematic break)

#### Scenario: Paragraphs
- **WHEN** source contains consecutive non-blank lines
- **THEN** they SHALL be joined into `<p>text</p>` with inline formatting applied
- **AND** a setext underline SHALL NOT be absorbed into the paragraph

#### Scenario: Fenced code blocks
- **WHEN** source contains lines between ``` or `~~~` fences (3+ characters, up to 3 spaces indent)
- **THEN** the output SHALL be `<pre><code>content</code></pre>`
- **AND** the fence info string's first word (entity-decoded) SHALL be emitted as `<code class="language-{word}">` when present
- **AND** the closing fence SHALL be at least as long as the opening fence and of the same character

#### Scenario: Indented code blocks
- **WHEN** source contains lines indented by 4+ columns outside a list context
- **THEN** they SHALL be emitted as `<pre><code>` blocks per CommonMark indented-code rules (including blank-line handling and interruption rules)

#### Scenario: Unordered and ordered lists
- **WHEN** source contains `-`/`+`/`*` bullet items or `1.`/`1)` ordered items
- **THEN** the output SHALL be `<ul>`/`<ol>` with `<li>` children per CommonMark list rules (marker consistency, start-number via `<ol start="N">` when N != 1, loose vs tight rendering, and block children inside items)
- **AND** tabs SHALL be normalized per column rules for indent calculation (never a fixed 2-space rule)

#### Scenario: Nested and mixed container structures
- **WHEN** source contains nested blockquotes (`> > inner`), blockquotes containing lists/headings/code, lazy continuation lines, or lists containing fenced code/headings/blockquotes
- **THEN** the container stack SHALL produce the CommonMark-specified nesting
- **AND** lazy continuation lines SHALL attach to the open paragraph per spec

#### Scenario: Thematic breaks
- **WHEN** source contains `---`, `***`, `___`, or spaced variants (`* * *`, `- - -`) on their own line (0-3 spaces indent)
- **THEN** the output SHALL be `<hr>`
- **AND** a `-`-based line directly under a paragraph line SHALL be a setext underline instead

#### Scenario: HTML blocks
- **WHEN** source contains any of the seven CommonMark HTML block types (including multi-line comments, processing instructions, declarations, and CDATA)
- **THEN** they SHALL be preserved as-is through their spec-defined end condition
- **AND** component tags (`<user-card>`) SHALL continue to pass through unchanged

#### Scenario: Link reference definitions absorbed
- **WHEN** source contains link reference definitions (`[label]: destination "title"`)
- **THEN** they SHALL produce no HTML output
- **AND** the definitions SHALL be retained on the parse result for inline resolution

#### Scenario: GFM tables
- **WHEN** source contains a header row, a valid delimiter row (`| --- | :-: | ---: |`), and zero or more body rows
- **THEN** the output SHALL be `<table><thead><tr><th>...` per GFM, with column alignment reflected per GFM output conventions and cell contents inline-rendered
- **AND** rows with mismatched cell counts SHALL be handled per GFM (excess dropped, missing filled empty)

#### Scenario: GFM task list items
- **WHEN** a list item begins with `[ ]`, `[x]`, or `[X]` followed by whitespace
- **THEN** the item SHALL begin with `<input type="checkbox" disabled="">` (plus `checked=""` when checked) per GFM
- **AND** the checkbox SHALL be static HTML with no reactive binding

### Requirement: List-body detection shall route for-loops to MarkdownForElement or repeat()

The `render_markdown` pipeline SHALL detect whether a `{% for %}` body is a list body and route accordingly: list bodies → `MarkdownForElement`; non-list bodies → standard `repeat()`. List-body detection SHALL use the block parser's list-item start condition as its single source of truth (no separate marker regex), so detection and parsing can never diverge.

#### Scenario: List body detected and routed to MarkdownForElement
- **WHEN** a `{% for %}` body consists of list-item lines per the block grammar (`-`, `*`, `+`, or ordered markers, including task-list markers)
- **THEN** a `MarkdownForElement` SHALL be created

#### Scenario: Non-list body routed to repeat()
- **WHEN** a `{% for %}` body consists of heading lines (`#`), paragraphs (plain text), or HTML blocks (`<div>`)
- **THEN** the standard `repeat()` path SHALL be used (fully reactive with reactive `{% if %}`)

#### Scenario: Non-list for preserves reactive if
- **WHEN** a non-list `{% for %}` body contains `{% if item.show %}...{% endif %}`
- **THEN** the `{% if %}` SHALL be bound via `switch()` and SHALL reactively update on `item.show` change

## ADDED Requirements

(none — new behaviors are folded into the MODIFIED requirements above)

## REMOVED Requirements

(none)
