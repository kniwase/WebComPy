# Spec: docs-site-documents

## ADDED Requirements

### Requirement: A manifest shall be the single source of truth for the docs structure

docs_app SHALL define a `DOCS_SECTIONS` manifest in `docs_app/docs_manifest.py`: an ordered list of sections, each with a `title` and an ordered list of page entries. Each page entry SHALL have `label` (nav label) and `path` (absolute route path), and exactly one of `source` (Markdown resource path, relative to the app package) or `component` (`"module:Attr"` lazy reference). The route children under `/documents`, the docs sidebar, the Navbar "Documents" dropdown, and Prev/Next ordering SHALL all be generated from this manifest. Paths SHALL be unique across the manifest.

#### Scenario: Routes generated from manifest

- **WHEN** the router is constructed
- **THEN** the `/documents` parent route's children correspond one-to-one with manifest page entries, in manifest order, each using `lazy()` loading

#### Scenario: Invalid entry rejected

- **WHEN** a manifest entry sets both `source` and `component`, or neither
- **THEN** a `WebComPyException` (or assertion error at import/validation time) identifies the offending entry

#### Scenario: Manifest consistency test

- **WHEN** the docs manifest unit test runs
- **THEN** it verifies paths are unique, every `source` file exists in `docs_app/documents/`, and generated routes match the manifest

### Requirement: The docs section shall use a nested-route shared layout

The `/documents` route SHALL be a parent route whose component (`DocsLayout`) renders a sectioned sidebar and a nested `RouterView`. Sibling navigation between docs pages SHALL preserve the layout instance (per RouterView level reuse), so sidebar state survives page transitions.

#### Scenario: Layout persists across sibling navigation

- **WHEN** a user navigates from one docs page to another docs page
- **THEN** the sidebar is not remounted and its interactive state (open sections, mobile toggle) is preserved

#### Scenario: Sidebar shows current page as active

- **WHEN** the user is on `/documents/getting-started/installation`
- **THEN** the corresponding sidebar `RouterLink` carries its `active_class` and `aria-current="page"`

### Requirement: Markdown docs pages shall be thin async wrappers over a shared template

Each Markdown-backed docs page component SHALL be an `async def` component that awaits `load_markdown_document(source)`, calls `context.set_title(...)` with the frontmatter title, and returns `docs_page_template(doc)`. The shared template SHALL render `doc.content` inside `<article class="prose">` and a right-hand TOC aside listing `doc.toc` entries as plain `<a href="#id">` links. The TOC aside SHALL be omitted when `doc.toc` is empty.

#### Scenario: Page renders Markdown with TOC

- **WHEN** a Markdown docs page with headings is visited
- **THEN** the article shows the rendered content with heading ids, and the TOC aside lists the headings in document order

#### Scenario: TOC anchor navigation

- **WHEN** a user clicks a TOC entry `<a href="#some-heading">`
- **THEN** the browser scrolls to the heading natively without any router navigation occurring

#### Scenario: SSR title

- **WHEN** any `/documents*` page is statically generated
- **THEN** the emitted HTML `<title>` contains the page's frontmatter title (all docs paths are non-root)

### Requirement: The docs layout shall provide Prev/Next navigation

`DocsLayout` SHALL render Prev/Next footer links computed reactively from the current route path and the flattened manifest page order. On the first page the Prev link SHALL be omitted; on the last page the Next link SHALL be omitted. Both Markdown and component-backed pages SHALL receive Prev/Next.

#### Scenario: Middle page shows both links

- **WHEN** the user is on the Quickstart page (between Installation and Signal Stream in manifest order)
- **THEN** the footer links to Installation (Prev) and Signal Stream (Next)

#### Scenario: Reactive update on navigation

- **WHEN** the user navigates between docs pages
- **THEN** the Prev/Next links update without the layout remounting

### Requirement: The existing signal-stream page shall join the docs section without URL change

The signal-stream page SHALL move from the flat route table into the `/documents` children via a manifest `component` entry. Its URL (`/documents/signal-stream`) SHALL NOT change, and its template content SHALL remain a Python component (no Markdown conversion).

#### Scenario: URL preserved

- **WHEN** `/documents/signal-stream` is requested
- **THEN** the SignalStream page renders inside `DocsLayout` with the sidebar visible

### Requirement: The Navbar "Documents" dropdown shall be generated from the manifest

The root layout's Navbar "Documents" entry SHALL populate its dropdown children from `DOCS_SECTIONS` (flattened page entries) instead of a hand-written list.

#### Scenario: Dropdown reflects manifest

- **WHEN** a page entry is added to the manifest
- **THEN** it appears in the Navbar "Documents" dropdown without any other code change

### Requirement: The docs section shall load the prose typography preset

docs_app SHALL add `/_webcompy-ui/prose.css` to the app head links. Only docs Markdown content SHALL opt into styling via the `.prose` wrapper class; other pages SHALL be unaffected.

#### Scenario: Stylesheet present in head

- **WHEN** any docs page HTML is inspected
- **THEN** a `<link rel="stylesheet" href="/_webcompy-ui/prose.css">` is present

### Requirement: The docs section shall be responsive

On wide viewports the layout SHALL show sidebar, content, and TOC. Below the wide breakpoint the TOC aside SHALL be hidden. Below the mobile breakpoint the sidebar SHALL collapse behind a toggle (following the Navbar mobile precedent), and content SHALL remain fully readable without either aside.

#### Scenario: Mobile layout

- **WHEN** a docs page is viewed on a narrow viewport
- **THEN** the sidebar is hidden until toggled and the TOC is not rendered visibly
