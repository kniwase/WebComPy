# Spec Delta

## MODIFIED Requirements

### Requirement: load_markdown_document shall load, split, and render a Markdown resource

`load_markdown_document(source: str | Path)` SHALL be an async public API exported from `webcompy.template`. It SHALL load the document text via `ResourcePort.load_text` (so SSR reads are recorded for hydration transfer), split frontmatter from the body, render the body with the document transforms (heading id injection, code block replacement, class map injection, and scrollable table wrapping via `<div class="prose-table-wrapper">` — each overridable via keyword arguments with documentation-oriented defaults), and extract the table of contents. It SHALL return a `MarkdownDocument`. Raw `render_markdown()` and `markdown-conformance` behavior SHALL remain unchanged.

#### Scenario: Loading a document in component setup

- **WHEN** `doc = await load_markdown_document("docs/getting-started.md")` is awaited inside an `async def` component setup
- **THEN** `doc.content` is the rendered element tree, `doc.metadata` holds the frontmatter, and `doc.toc` lists the headings

#### Scenario: Tables in document mode are wrapped for horizontal scrolling

- **WHEN** a Markdown document containing a GFM table is loaded with `load_markdown_document`
- **THEN** the rendered `<table>` in `doc.content` SHALL be wrapped in a `<div class="prose-table-wrapper">` container
- **AND** calling `render_markdown()` directly on the same table SHALL continue to emit a bare `<table>` with no wrapper

#### Scenario: SSR resource transfer

- **WHEN** a document is loaded during server-side rendering
- **THEN** the resource read is recorded by `ServerResourcePort` so the browser does not refetch the file during hydration

### Requirement: A prose typography preset stylesheet shall be provided opt-in

The framework SHALL ship a `prose.css` stylesheet under `webcompy/ui/_styles/`, registered in `_STYLES_FILES` so it is served at `/_webcompy-ui/prose.css` and copied during SSG like the other framework stylesheets. It SHALL NOT be imported by `index.css`. All rules SHALL be scoped under a `.prose` wrapper class and wrapped in `@layer prose`. Colors, spacing, and fonts SHALL reference the existing `tokens.css` CSS variables so the preset follows the active theme. The preset SHALL cover headings, paragraphs, lists, tables, blockquotes, horizontal rules, inline code, and code blocks. Code blocks SHALL receive symmetric vertical spacing (`margin: var(--space-4) 0`) from a `.prose pre` rule. Wide tables SHALL scroll horizontally inside `.prose .prose-table-wrapper` (`max-width: 100%; overflow-x: auto;`) without expanding their parent container; `.prose :not(pre) > code`, headings, and paragraphs SHALL wrap long unbroken identifiers/URLs safely on narrow viewports (`overflow-wrap: anywhere` or equivalent); and `.prose img` SHALL constrain `max-width: 100%; height: auto;`. `prose.css` SHALL declare the cascade layer order (`@layer reset, tokens, components, prose, webcompy-scope`) before its rules so the `prose` layer is ordered after `components` regardless of stylesheet load order, and the code block stylesheet (`code-block.css`) SHALL be wrapped in `@layer components` so the layered preset rule takes precedence over the block's base `margin: 0`.

#### Scenario: Stylesheet served and copied

- **WHEN** the dev server or SSG output is inspected
- **THEN** `prose.css` is available at `/_webcompy-ui/prose.css` alongside the other framework stylesheets without being linked automatically

#### Scenario: Scoped and themed rules

- **WHEN** `prose.css` content is inspected
- **THEN** every rule selector is scoped under `.prose`, the rules live in `@layer prose`, and color/font values reference `tokens.css` variables rather than hard-coded values

#### Scenario: Wide tables and long inline code do not overflow container

- **WHEN** `prose.css` styles a `.prose` article containing a wide `.prose-table-wrapper > table` and long unbroken inline `<code>` spans inside a narrow or desktop-constrained column
- **THEN** `.prose-table-wrapper` scrolls horizontally within the column width and inline `<code>` wraps within the column without pushing `.prose` wider than its container

#### Scenario: Code blocks have symmetric vertical spacing

- **WHEN** `prose.css` content is inspected
- **THEN** it contains a `.prose pre` rule setting `margin: var(--space-4) 0`

#### Scenario: Prose layer declared after components

- **WHEN** `prose.css` content is inspected
- **THEN** it declares the cascade layer order `@layer reset, tokens, components, prose, webcompy-scope` before its `@layer prose` rules

#### Scenario: Code block stylesheet participates in the layer system

- **WHEN** `code-block.css` content is inspected
- **THEN** its rules are wrapped in `@layer components`
