# Spec: markdown-document

## ADDED Requirements

### Requirement: Flat frontmatter blocks shall parse key-value string metadata

A Markdown document whose first line is exactly `---` SHALL be treated as having a flat frontmatter block terminated by the next line that is exactly `---`. Each non-empty line inside the block SHALL be parsed as `key: value`, producing a `dict[str, str]` entry with surrounding whitespace stripped. Lines without a colon SHALL raise `WebComPyException`. The remainder of the source after the closing delimiter SHALL be treated as the Markdown body.

#### Scenario: Flat frontmatter extraction

- **WHEN** a document starts with `---`, the lines `title: Getting Started` and `section: guide`, a closing `---`, and a Markdown body
- **THEN** metadata is `{"title": "Getting Started", "section": "guide"}` and the body excludes the frontmatter block

#### Scenario: Document without frontmatter

- **WHEN** a document's first line is not a frontmatter delimiter
- **THEN** metadata is empty and the entire source is the Markdown body

#### Scenario: Malformed flat frontmatter line

- **WHEN** a flat frontmatter block contains a line without a colon
- **THEN** `WebComPyException` is raised identifying the offending line

### Requirement: TOML frontmatter blocks shall parse structured metadata

A Markdown document whose first line is exactly `+++` SHALL be treated as having a TOML frontmatter block terminated by the next line that is exactly `+++`. The block SHALL be parsed with stdlib `tomllib`, producing a `dict[str, Any]` that may contain nested tables and arrays. TOML parse failures SHALL raise `WebComPyException` wrapping the TOML error.

#### Scenario: TOML frontmatter with nested structures

- **WHEN** a document starts with `+++`, contains `title = "Guide"` and a `[page]` table with `order = 2`, and a closing `+++`
- **THEN** metadata is `{"title": "Guide", "page": {"order": 2}}` and the body excludes the frontmatter block

#### Scenario: Invalid TOML

- **WHEN** a `+++` frontmatter block is not valid TOML
- **THEN** `WebComPyException` is raised including the TOML parse error message

### Requirement: load_markdown_document shall load, split, and render a Markdown resource

`load_markdown_document(source: str | Path)` SHALL be an async public API exported from `webcompy.template`. It SHALL load the document text via `ResourcePort.load_text` (so SSR reads are recorded for hydration transfer), split frontmatter from the body, render the body with the document transforms (heading id injection, code block replacement, class map injection — each overridable via keyword arguments with documentation-oriented defaults), and extract the table of contents. It SHALL return a `MarkdownDocument`.

#### Scenario: Loading a document in component setup

- **WHEN** `doc = await load_markdown_document("docs/getting-started.md")` is awaited inside an `async def` component setup
- **THEN** `doc.content` is the rendered element tree, `doc.metadata` holds the frontmatter, and `doc.toc` lists the headings

#### Scenario: SSR resource transfer

- **WHEN** a document is loaded during server-side rendering
- **THEN** the resource read is recorded by `ServerResourcePort` so the browser does not refetch the file during hydration

### Requirement: MarkdownDocument shall bundle content, metadata, and toc

`load_markdown_document` SHALL return an immutable `MarkdownDocument` dataclass with fields `content: ElementAbstract`, `metadata: Mapping[str, Any]`, and `toc: tuple[HeadingInfo, ...]`. `HeadingInfo` SHALL carry `level: int` (1–6), `text: str` (resolved heading text), and `id: str` (the slug id injected into the heading element). TOC ids SHALL always match the ids present in `content`.

#### Scenario: Result structure

- **WHEN** a document with frontmatter and three headings is loaded
- **THEN** `MarkdownDocument.metadata` equals the parsed frontmatter, `MarkdownDocument.toc` has three `HeadingInfo` entries in document order, and each entry's `id` exists on the corresponding heading element in `content`

### Requirement: TOC extraction shall resolve heading text and levels from the element tree

TOC extraction SHALL walk the rendered element tree (including fragments and template-directive subtrees rendered at setup time), collect `<h1>`–`<h6>` elements in document order, resolve heading text from text-node descendants (resolving `Computed`-wrapped text to its current value), and pair each with the slug id injected by the heading id transform. Headings nested inside dynamic subtrees that cannot be statically inspected MAY be omitted from the TOC.

#### Scenario: Headings collected in document order

- **WHEN** a document contains an `<h1>`, two `<h2>`s, and an `<h3>` nested in a `{% for %}` block
- **THEN** the TOC lists all resolvable headings in document order with their levels and ids

#### Scenario: Interpolated heading text

- **WHEN** a heading contains `{{ title }}` bound to a signal with value `"Intro"`
- **THEN** the TOC entry's `text` is `"Intro"`

### Requirement: A prose typography preset stylesheet shall be provided opt-in

The framework SHALL ship a `prose.css` stylesheet under `webcompy/ui/_styles/`, registered in `_STYLES_FILES` so it is served at `/_webcompy-ui/prose.css` and copied during SSG like the other framework stylesheets. It SHALL NOT be imported by `index.css`. All rules SHALL be scoped under a `.prose` wrapper class and wrapped in `@layer prose`. Colors, spacing, and fonts SHALL reference the existing `tokens.css` CSS variables so the preset follows the active theme. The preset SHALL cover headings, paragraphs, lists, tables, blockquotes, horizontal rules, and inline code.

#### Scenario: Stylesheet served and copied

- **WHEN** the dev server or SSG output is inspected
- **THEN** `prose.css` is available at `/_webcompy-ui/prose.css` alongside the other framework stylesheets without being linked automatically

#### Scenario: Scoped and themed rules

- **WHEN** `prose.css` content is inspected
- **THEN** every rule selector is scoped under `.prose`, the rules live in `@layer prose`, and color/font values reference `tokens.css` variables rather than hard-coded values
