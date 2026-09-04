# Docs Site Documents

## Purpose

The documentation section of the docs_app (`/documents`) presents framework documentation as static-looking pages: a manifest-driven route table, a nested-route shared layout with a sectioned sidebar and Prev/Next paging, thin async Markdown page wrappers over a shared template with a right-hand TOC, and a prose typography preset. A single manifest (`DOCS_SECTIONS` plus a `DOCS_INDEX` entry) is the single source of truth from which the routes, sidebar, Navbar "Documents" dropdown, and Prev/Next ordering all derive.
## Requirements
### Requirement: A manifest shall be the single source of truth for the docs structure

docs_app SHALL define a `DOCS_SECTIONS` manifest in `docs_app/docs_manifest.py`: an ordered list of sections, each with a `title` and an ordered list of page entries. Each page entry SHALL have `label` (nav label) and `path` (absolute route path), and exactly one of `source` (Markdown resource path, relative to the app package) or `component` (`"module:Attr"` lazy reference). docs_app SHALL also define a `DOCS_INDEX` entry representing the `/documents` index route. The route children under `/documents` SHALL be generated from the manifest (the `DOCS_INDEX` entry first, then the section page entries in order). The docs sidebar, the Navbar "Documents" dropdown, and Prev/Next ordering SHALL be generated from the section page entries only — the index SHALL NOT appear in navigation or paging. Paths SHALL be unique across the manifest. Every page path SHALL equal the docs root (`DOCS_ROOT`) or be a path under it, so the manifest-owned routes always live inside the `/documents` subtree. Page paths SHALL additionally follow the category section model prefixes defined by that requirement.

#### Scenario: Routes generated from manifest

- **WHEN** the router is constructed
- **THEN** the `/documents` parent route's children correspond one-to-one with manifest entries (the `DOCS_INDEX` entry followed by the section page entries), in manifest order, each using `lazy()` loading

#### Scenario: Invalid entry rejected

- **WHEN** a manifest entry sets both `source` and `component`, or neither
- **THEN** a `WebComPyException` (or assertion error at import/validation time) identifies the offending entry

#### Scenario: Path outside docs root rejected

- **WHEN** a manifest entry's `path` is not equal to `DOCS_ROOT` and does not start with `DOCS_ROOT + "/"`
- **THEN** a `WebComPyException` at import/validation time identifies the offending entry

#### Scenario: Manifest consistency test

- **WHEN** the docs manifest unit test runs
- **THEN** it verifies paths are unique, every `source` file exists in `docs_app/documents/`, and generated routes match the manifest

### Requirement: The docs manifest shall follow the category section model

The `DOCS_SECTIONS` manifest SHALL consist of top-level category sections in the order `Getting Started`, `Basic Usage`, `Advanced Usage`, with a `Guides` category inserted between `Getting Started` and `Basic Usage` when tutorial pages exist. Each page's manifest `path` SHALL start with the category's URL prefix: `/documents/getting-started/`, `/documents/guides/`, `/documents/basic/`, or `/documents/advanced/`. Section titles other than these category names SHALL NOT be introduced by structural changes. A category without pages SHALL be omitted from the manifest rather than carried as an empty section, and manifest validation SHALL reject a section that omits its `title` or contains an empty `pages` list.

#### Scenario: Page paths carry the category prefix

- **WHEN** the manifest is validated
- **THEN** every page entry's `path` starts with its category's prefix, and the category sections appear in the defined order

#### Scenario: Empty section rejected

- **WHEN** the manifest is validated and a category section has an empty `pages` list
- **THEN** a `WebComPyException` at import/validation time identifies the offending section

#### Scenario: Missing section title rejected

- **WHEN** the manifest is validated and a section omits its `title`
- **THEN** a `WebComPyException` at import/validation time identifies the offending section

### Requirement: The docs section shall use a nested-route shared layout

The `/documents` route SHALL be a parent route whose component (`DocsLayout`) renders a sectioned sidebar and a nested `RouterView`. Sibling navigation between docs pages SHALL preserve the layout instance (per RouterView level reuse), so the section-open sidebar state survives page transitions. The transient mobile sidebar overlay SHALL close when a navigation completes, so the destination page is unobstructed on narrow viewports.

#### Scenario: Layout persists across sibling navigation

- **WHEN** a user navigates from one docs page to another docs page
- **THEN** the sidebar is not remounted and its section-open state is preserved
- **AND** the mobile sidebar overlay is closed after the navigation completes

#### Scenario: Sidebar shows current page as active

- **WHEN** the user is on `/documents/getting-started/installation`
- **THEN** the corresponding sidebar `RouterLink` carries its `active_class` and `aria-current="page"`

### Requirement: Markdown docs pages shall be thin async wrappers over a shared template

Each Markdown-backed docs page component SHALL be an `async def` component that awaits `load_markdown_document(source)`, calls `context.set_title(...)` with the frontmatter title, and returns `docs_page_template(doc, context.path)`. The shared template SHALL render `doc.content` inside `<article class="prose">` and a right-hand TOC aside listing `doc.toc` entries as plain `<a>` links with absolute-path fragment hrefs (`{current_path}#{id}`, where `current_path` is the page's `RouterContext.path`). The href SHALL preserve the trailing-slash form of `current_path` so the anchor stays a same-document fragment navigation. The TOC aside SHALL be omitted when `doc.toc` is empty.

#### Scenario: Page renders Markdown with TOC

- **WHEN** a Markdown docs page with headings is visited
- **THEN** the article shows the rendered content with heading ids, and the TOC aside lists the headings in document order

#### Scenario: TOC anchor navigation

- **WHEN** a user clicks a TOC entry `<a href="/documents/getting-started/installation/#some-heading">`
- **THEN** the browser scrolls to the heading natively without any router navigation occurring

#### Scenario: SSR title

- **WHEN** any `/documents*` page is statically generated
- **THEN** the emitted HTML `<title>` contains the page's frontmatter title (all docs paths are non-root)

### Requirement: Docs body cross-links shall use rendered-site URLs

Cross-document links inside `docs_app/documents/*.md` bodies SHALL use absolute rendered-site URLs (category-prefixed paths, optionally with a `#heading-id` fragment) and SHALL NOT link to `.md` source files. A unit test SHALL scan all docs Markdown bodies for link targets ending in `.md` and fail when any is found. The same scan SHALL fail when any absolute `/documents`-rooted link target, after stripping a `#heading-id` fragment and a trailing slash, matches neither the docs root nor a manifest page path.

#### Scenario: Relative source-file link rejected

- **WHEN** a docs body contains `[Text](./other.md)`
- **THEN** the docs link scan test fails naming the file and line

#### Scenario: Cross-page anchor link is valid

- **WHEN** a docs body links to `/documents/advanced/websocket#the-gaprefetch-recipe`
- **THEN** the scan test passes and the browser performs a same-path anchor navigation

#### Scenario: Unknown target rejected

- **WHEN** a docs body links to an absolute `/documents/...` path that is not a manifest page path (ignoring any `#heading-id` fragment)
- **THEN** the docs link scan test fails naming the file and line

### Requirement: The docs layout shall provide Prev/Next navigation

`DocsLayout` SHALL render Prev/Next footer links computed reactively from the current route path and the flattened manifest page order. On the first page the Prev link SHALL be omitted; on the last page the Next link SHALL be omitted. Both Markdown and component-backed pages SHALL receive Prev/Next. Paging crosses category boundaries in manifest order.

#### Scenario: Middle page shows both links

- **WHEN** the user is on any docs page that is neither first nor last in flattened manifest order
- **THEN** the footer links to its predecessor (Prev) and successor (Next), even across category boundaries

#### Scenario: Reactive update on navigation

- **WHEN** the user navigates between docs pages
- **THEN** the Prev/Next links update without the layout remounting

### Requirement: The Navbar "Documents" dropdown shall be generated from the manifest

The root layout's Navbar "Documents" entry SHALL populate its dropdown children from `DOCS_SECTIONS` (flattened page entries) instead of a hand-written list.

#### Scenario: Dropdown reflects manifest

- **WHEN** a page entry is added to the manifest
- **THEN** it appears in the Navbar "Documents" dropdown without any other code change

### Requirement: The Navbar dropdown state shall be read-only snapshot state driven by state-event composables

The docs_app Navbar SHALL manage measured dropdown positions as a single read-only snapshot signal created with `use_readonly_signal({})`, holding a dict of dropdown index to `(top, right)` position tuples, with the composable's update function as the sole write path. Scroll (document) and resize (window) state events SHALL be bridged via `use_document_event` / `use_window_event`, whose `transform` re-measures the open dropdowns, writes the fresh snapshot through the update function, and returns it; an unchanged snapshot SHALL NOT notify consumers. Toggling a dropdown SHALL measure immediately after opening and write through the same update function. The outside-click listener SHALL remain a manually registered document listener with `on_before_destroy` cleanup, since every outside click must close the menus (occurrence semantics, not state-event semantics).

#### Scenario: Dropdown follows its toggle on scroll or resize

- **WHEN** a dropdown is open and a scroll or resize event fires
- **THEN** the dropdown position re-measures from its toggle element
- **AND** the snapshot updates only when a measured position actually changed

#### Scenario: Toggle measures immediately

- **WHEN** the user clicks a dropdown toggle
- **THEN** the dropdown opens at the toggle's current position without waiting for a scroll or resize event

#### Scenario: Outside click closes all dropdowns on every occurrence

- **WHEN** the user clicks anywhere outside the dropdowns
- **THEN** every open dropdown closes, and the closing is driven by the manual listener rather than by a state-event composable

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

