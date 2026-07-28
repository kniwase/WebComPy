# Delta Spec: template-engine

## MODIFIED Requirements

### Requirement: DefaultMarkdownParser shall convert Markdown to HTML

`DefaultMarkdownParser.render(source)` SHALL convert Markdown text to HTML strings using a two-phase CommonMark parser (block structure per the container-stack algorithm; inline content per the delimiter-run algorithm), extended with the GFM extensions (tables, task list items, strikethrough, autolinks, disallowed raw HTML). `textwrap.dedent` SHALL be applied to multi-line sources at the framework layer (`render_markdown`) only; the parser itself SHALL NOT dedent. Tabs SHALL be handled per CommonMark (advance to the next 4-column stop, with partial-tab support); no global tab-to-spaces normalization SHALL be performed.

Inline parsing SHALL be implemented as a character-scanning tokenizer followed by delimiter-stack processing (not sequential regex substitution), and SHALL be linear-time for adversarial inputs.

#### Scenario: ATX headings
- **WHEN** source contains `# Title` through `###### Sub`
- **THEN** the output SHALL be `<h1>Title</h1>` through `<h6>Sub</h6>`
- **AND** closing hash sequences preceded by a space (`## Title ##`) SHALL be stripped
- **AND** `#hashtag` (no space after `#`) SHALL NOT be a heading

#### Scenario: Setext headings
- **WHEN** source contains `Title` followed by an underline of `=` characters
- **THEN** the output SHALL be `<h1>Title</h1>`
- **AND** an underline of `-` characters SHALL produce `<h2>Title</h2>` (not a thematic break)

#### Scenario: Paragraphs and line breaks
- **WHEN** source contains consecutive non-blank lines
- **THEN** they SHALL be joined into `<p>text</p>` with soft breaks preserved as newlines per spec
- **AND** a line ending in two or more spaces or a backslash SHALL produce `<br>` (hard break)

#### Scenario: Fenced code blocks
- **WHEN** source contains lines between ``` or `~~~` fences
- **THEN** the output SHALL be `<pre><code>content</code></pre>`
- **AND** the fence info string's first word (entity-decoded) SHALL be emitted as `<code class="language-{word}">` when present

#### Scenario: Indented code blocks
- **WHEN** source contains lines indented by 4+ columns outside a list context
- **THEN** they SHALL be emitted as `<pre><code>` blocks per CommonMark indented-code rules

#### Scenario: Lists
- **WHEN** source contains `-`/`+`/`*` bullet items or `1.`/`1)` ordered items
- **THEN** the output SHALL follow CommonMark list rules (marker consistency, `<ol start="N">` when N != 1, loose vs tight rendering, block children inside items)

#### Scenario: Nested and mixed container structures
- **WHEN** source contains nested blockquotes, blockquotes containing lists/headings/code, lazy continuation lines, or lists containing fenced code/headings/blockquotes
- **THEN** the container stack SHALL produce the CommonMark-specified nesting

#### Scenario: Thematic breaks
- **WHEN** source contains `---`, `***`, `___`, or spaced variants on their own line
- **THEN** the output SHALL be `<hr>` unless the line acts as a setext underline

#### Scenario: HTML blocks
- **WHEN** source contains any of the seven CommonMark HTML block types
- **THEN** they SHALL be preserved as-is through their spec-defined end condition
- **AND** component tags (`<user-card>`) SHALL continue to pass through unchanged

#### Scenario: Link reference definitions absorbed
- **WHEN** source contains link reference definitions
- **THEN** they SHALL produce no HTML output and SHALL be retained for inline reference resolution

#### Scenario: GFM tables
- **WHEN** source contains a header row, a valid delimiter row, and zero or more body rows
- **THEN** the output SHALL be `<table>` per GFM with column alignment and inline-rendered cell contents

#### Scenario: GFM task list items
- **WHEN** a list item begins with `[ ]`, `[x]`, or `[X]` followed by whitespace
- **THEN** the item SHALL begin with `<input type="checkbox" disabled="">` (plus `checked=""` when checked), static and non-reactive

#### Scenario: Emphasis and strong via delimiter runs
- **WHEN** source contains `*`/`_` delimiters in any spec-valid configuration
- **THEN** `<em>`/`<strong>` SHALL be produced per the CommonMark delimiter algorithm, including `***bold-italic***`, nested forms (`*a **b** c*`), and intraword underscore rules (`foo_bar_baz` remains literal; `_em_` and `__strong__` are active)
- **NOTE**: Symmetric delimiter runs of length ≥4 (e.g. `****foo****`) produce nested `<strong>` levels matching commonmark.js/py and markdown-it behavior, rather than collapsing to a single level (as cmark-gfm does). This is a documented ecosystem-wide divergence: the portable reference implementations (commonmark.js, commonmark.py) share the same nested behavior; only the C cmark-gfm collapses. The WebComPy parser matches the broader ecosystem. See `openspec/changes/refactor-markdown-inline-parser/specs/markdown-conformance/spec.md` for the deviation catalog.

#### Scenario: GFM strikethrough
- **WHEN** source contains `~` or `~~` delimiters per the GFM extension
- **THEN** `<del>` SHALL be produced per the delimiter algorithm

#### Scenario: Code spans
- **WHEN** source contains backtick strings of any length (`` `a` ``, `` ``a`b`` ``)
- **THEN** matching variable-length code spans SHALL be produced per spec
- **AND** content SHALL be HTML-escaped but otherwise literal (no emphasis, entities, or template processing inside)

#### Scenario: Backslash escapes and entities
- **WHEN** source contains backslash-escaped punctuation (`\*`) or entity/numeric references (`&copy;`, `&#65;`, `&#x41;`)
- **THEN** escapes SHALL yield the literal punctuation character and references SHALL resolve per spec (via stdlib `html.entities`), except inside code spans/blocks where both remain literal

#### Scenario: Links and images
- **WHEN** source contains inline links/images with balanced-paren or `<...>` destinations and optional titles (`"..."`, `'...'`, `(...)`), or full/collapsed/shortcut reference links
- **THEN** `<a href>`/`<img src>` SHALL be produced per spec, with titles and reference resolution via the block-layer definition table (CommonMark label normalization)

#### Scenario: Autolinks and GFM extended autolinks
- **WHEN** source contains `<scheme:...>`, `<email>`, `www.example.com`, bare URLs, or bare email addresses
- **THEN** links SHALL be produced per CommonMark/GFM rules including trailing-punctuation trimming
- **AND** destinations from inline links, reference links, and images SHALL pass the URL scheme allow-list (`http`/`https`/`mailto`/relative/`#fragment`); disallowed schemes render as literal text (no element)
- **AND** destinations from CommonMark angle-bracket autolinks and GFM extended autolinks SHALL be subject to a deny-list only (`javascript:`/`data:`/`vbscript:` render as literal text); any other syntactically valid scheme (e.g. `irc:`, `ftp:`, unknown schemes) produces a link per the GFM spec, because autolinks display their URL as text and thus carry no phishing surface

#### Scenario: GFM disallowed raw HTML
- **WHEN** source contains raw HTML tags in the GFM disallowed set (`title`, `textarea`, `style`, `xmp`, `iframe`, `noembed`, `noframes`, `script`, `plaintext`) as **inline HTML** or as **HTML blocks of types 2-7**
- **THEN** the leading `<` of those tags SHALL be entity-escaped (`&lt;`) in the Markdown→HTML output
- **AND** HTML blocks of **type 1** (`<script>`, `<pre>`, `<style>`, `<textarea>` raw-text containers) SHALL pass through verbatim, because the GFM spec suite pins verbatim output for those examples (filtering them would break conformance)
- **AND** the template binding layer's rejection of `script`/`style`/`iframe`/`noembed`/`noframes`/`xmp` remains as a separate, unchanged policy; note that `<textarea>`, `<title>`, and `<plaintext>` type-1 blocks are NOT rejected by the binding layer and therefore flow into the DOM verbatim (residual raw-HTML surface; rely on a downstream HTML sanitizer if Markdown is untrusted)

## ADDED Requirements

(none)

## REMOVED Requirements

(none)
