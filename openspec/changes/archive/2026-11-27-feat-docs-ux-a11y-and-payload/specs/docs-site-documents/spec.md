# Spec Delta

## MODIFIED Requirements

### Requirement: The docs section shall use a nested-route shared layout

The `/documents` route SHALL be a parent route whose component (`DocsLayout`) renders a sectioned sidebar and a nested `RouterView`. Sibling navigation between docs pages SHALL preserve the layout instance (per RouterView level reuse), so the section-open sidebar state survives page transitions. The transient mobile sidebar overlay SHALL close when a navigation completes, so the destination page is unobstructed on narrow viewports. On desktop viewports, sticky `.docs-sidebar` and `.docs-toc` panels SHALL have viewport-bounded `max-height` and independent vertical scrolling (`overflow-y: auto`) so long navigation lists or multi-screen TOCs remain reachable without trapping items below the fold. Shared docs-page layout styling SHALL NOT be duplicated as separate identical `<style data-webcompy-cid>` elements across every lazy page module.

#### Scenario: Layout persists across sibling navigation

- **WHEN** a user navigates from one docs page to another docs page
- **THEN** the sidebar is not remounted and its section-open state is preserved
- **AND** the mobile sidebar overlay is closed after the navigation completes

#### Scenario: Sidebar shows current page as active

- **WHEN** the user is on `/documents/getting-started/installation`
- **THEN** the corresponding sidebar `RouterLink` carries its `active_class` and `aria-current="page"`

#### Scenario: Long sidebar and TOC scroll independently without duplicating page styles

- **WHEN** a user opens `/documents/api/server-and-cli/` on desktop
- **THEN** `.docs-sidebar` and `.docs-toc` are height-bounded within the viewport with independent vertical scrollbars
- **AND** `<head>` contains at most one shared rule set for docs page layout rather than one duplicate copy per route module

### Requirement: Markdown docs pages shall be thin async wrappers over a shared template

Each Markdown-backed docs page component SHALL be an `async def` component that awaits `load_markdown_document(source)`, calls `context.set_title(...)` with the frontmatter title, and returns `docs_page_template(doc, context.path)`. The shared template SHALL render `doc.content` inside `<article class="prose">` with opt-in copyable code blocks and clickable `#` heading anchor links, and a right-hand TOC aside listing `doc.toc` entries as plain `<a>` links with absolute-path fragment hrefs (`{current_path}#{id}`, where `current_path` is the page's `RouterContext.path`). The href SHALL preserve the trailing-slash form of `current_path` so the anchor stays a same-document fragment navigation. The TOC aside SHALL be omitted when `doc.toc` is empty.

#### Scenario: Page renders Markdown with TOC

- **WHEN** a Markdown docs page with headings is visited
- **THEN** the article shows the rendered content with heading ids, and the TOC aside lists the headings in document order

#### Scenario: TOC anchor navigation

- **WHEN** a user clicks a TOC entry `<a href="/documents/getting-started/installation/#some-heading">`
- **THEN** the browser scrolls to the heading natively without any router navigation occurring

#### Scenario: SSR title

- **WHEN** any `/documents*` page is statically generated
- **THEN** the emitted HTML `<title>` contains the page's frontmatter title (all docs paths are non-root)

### Requirement: The Navbar "Documents" dropdown shall be generated from the manifest

The root layout's Navbar "Documents" entry SHALL populate its dropdown children from `DOCS_SECTIONS` grouped by category section inside a viewport-bounded scrollable panel instead of a flat unbounded list of links.

#### Scenario: Dropdown reflects manifest

- **WHEN** a page entry is added to the manifest
- **THEN** it appears in the Navbar "Documents" dropdown under its category section without any other code change
- **AND** the dropdown menu height fits comfortably within typical desktop viewports with vertical scroll

## ADDED Requirements

### Requirement: Docs site SHALL bake only route-used resource payloads in static HTML

`docs_app/webcompy_config.py` SHALL configure `resource_transfer="used"` (rather than `"all-text"`) so statically generated pages embed only the resource(s) actually consumed by that page, while client-side navigation fetches unloaded Markdown documents on demand without blocking initial hydration.

#### Scenario: Static Home page excludes all-page Markdown bundle

- **WHEN** the static `docs/` output is generated via `webcompy generate`
- **THEN** `docs/index.html`'s `__webcompy_data__` payload SHALL NOT embed the text of all 81 documentation Markdown files
- **AND** navigating to `/documents/...` on the client continues to load Markdown pages via `ResourcePort`

### Requirement: Docs site SHALL provide accessible landmarks, language attribute, controls, and heading hierarchy

`docs_app` SHALL emit `<html lang="en">` via `set_html_attr`, render a keyboard-focusable skip-to-content link targeting the main content landmark, provide distinct `aria-label` attributes on navigation landmarks (primary navbar, docs sidebar, table of contents, Prev/Next pagination), use a semantic `RouterLink` home link for `.navbar-brand`, implement `ThemeToggle` as a standard cycle `<button>` with accessible SVG icon and live state `aria-label` (never a 2-state `role="switch"`), maintain sequential `H1 -> H2` heading hierarchy across `DemoDisplay` example sections, and render the `404` page with centered layout and direct recovery links to Home and Documentation. Furthermore, `/documents/basic/ui-primitives`, `/documents/basic/overlay`, and `/documents/basic/disclosure` SHALL position their live interactive demo sections ahead of `Next steps`.

#### Scenario: Automated accessibility landmark and control audit passes

- **WHEN** any docs_app page HTML/DOM is inspected
- **THEN** `<html lang="en">`, a skip link, uniquely labeled `<nav>` landmarks, a clickable home brand link, a non-`switch` `ThemeToggle` button, and monotonic heading levels are present

#### Scenario: Not Found page offers recovery navigation

- **WHEN** a user lands on an unmatched URL rendering `NotFound`
- **THEN** the page displays a structured card with links back to Home (`/`) and Getting Started (`/documents/getting-started/what-is-webcompy`)

### Requirement: Docs site SHALL provide client-side documentation search

`docs_app` SHALL provide a client-side documentation search UI (accessible from the Navbar and keyboard shortcut) that filters `DOCS_SECTIONS` page entries by title, category, description/keywords, and path, and navigates directly to the selected route using the router.

#### Scenario: Filtering and navigating to a docs page via search

- **WHEN** a user opens the documentation search UI and enters `"hydration"`
- **THEN** matching pages (such as `Hydration and Transfer`) are listed with category context and selecting one navigates to its route
