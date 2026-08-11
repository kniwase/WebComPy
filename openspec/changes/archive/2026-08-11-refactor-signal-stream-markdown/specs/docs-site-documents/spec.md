# docs-site-documents delta: refactor-signal-stream-markdown

## MODIFIED Requirements

### Requirement: The docs layout shall provide Prev/Next navigation

`DocsLayout` SHALL render Prev/Next footer links computed reactively from the current route path and the flattened manifest page order. On the first page the Prev link SHALL be omitted; on the last page the Next link SHALL be omitted. Both Markdown and component-backed pages SHALL receive Prev/Next.

#### Scenario: Middle page shows both links

- **WHEN** the user is on the Quickstart page (between Installation and Signals and Streams in manifest order)
- **THEN** the footer links to Installation (Prev) and Signals and Streams (Next)

#### Scenario: Reactive update on navigation

- **WHEN** the user navigates between docs pages
- **THEN** the Prev/Next links update without the layout remounting

### Requirement: The existing signal-stream page shall join the docs section without URL change

The signal-stream page SHALL be a Markdown-backed docs page served from the `/documents` children via a manifest `source` entry (`documents/signal_stream.md`). Its URL (`/documents/signal-stream`) SHALL NOT change. The page SHALL be rendered through `docs_page_template` like the other Markdown docs pages, and its manifest label, frontmatter title, and H1 SHALL all be "Signals and Streams".

#### Scenario: URL preserved

- **WHEN** `/documents/signal-stream` is requested
- **THEN** the Signals and Streams page renders inside `DocsLayout` with the sidebar visible

#### Scenario: Markdown rendering with TOC

- **WHEN** `/documents/signal-stream` is requested
- **THEN** the article shows the rendered Markdown content with heading ids, and the TOC aside lists the page headings in document order
