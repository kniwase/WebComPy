# Proposal

## Why

The production audit of `https://www.webcompy.net/` identified systemic usability, accessibility, navigation, and bundle-size issues across the documentation shell and landing page: an initial HTML document size of `741 KB` (embedding `1.26 MB` of pre-rendered text for all 81 routes plus ~80 duplicate copies of `DOCS_PAGE_SCOPED_STYLE` totaling `170 KB` of `<style>` tags), unbounded sticky sidebars (`3,465px`) and TOCs (`4,690px`), an unsearchable `2,993px` flat Navbar dropdown of 80 links, missing accessibility landmarks (`<html lang>`, skip link, `<nav aria-label>`, semantic brand link, `H1→H3` heading skips, and misapplied `role="switch"` on `ThemeToggle`), unpolished `404` and Home feature-grid spacing, and missing documentation conveniences (one-click `CodeBlock` copy, clickable `#` heading anchor links, and client-side search).

## What Changes

- **Payload & `<style>` deduplication (`docs-site-documents`)**: Configure `docs_app/webcompy_config.py` to use `resource_transfer="used"` (baking only the rendered route's Markdown resource instead of `"all-text"` for all 81 routes, with on-demand fetch for client navigation), and eliminate ~80 duplicated `<style data-webcompy-cid>` blocks for `DOCS_PAGE_SCOPED_STYLE` by moving shared docs page layout CSS into a single stylesheet rule or shared layout wrapper.
- **Navigation, sticky scrolling & client-side search (`docs-site-documents`)**: Bound `.docs-sidebar` and `.docs-toc` to viewport-relative `max-height` with independent `overflow-y: auto` scrolling, replace the 80-item flat Navbar `Documents` dropdown with a categorized scrollable panel, and add client-side documentation search (triggered from Navbar/shortcut over a lightweight manifest/section index).
- **Accessibility & landmark semantics (`docs-site-documents`, `docs-site-home`)**: Set `<html lang="en">` via `set_html_attr`, add a skip-to-content link, give navigation regions distinct `aria-label` values, replace non-semantic `<span class="navbar-brand">` with a home link, fix `ThemeToggle` ARIA semantics away from 2-state `role="switch"` with an accessible SVG icon, align `DemoDisplay` section titles (`H2`) cleanly with page heading hierarchy, refine Home's feature-card grid balance and card margins (`docs-site-home`), elevate live demos before `Next steps` on UI primitive/overlay/disclosure docs, and polish the `404` page with centered layout and recovery links.
- **Reader ergonomics: copyable `CodeBlock` & heading `#` permalinks (`code-block`, `markdown-document`, `docs-site-documents`)**: Add an opt-in `copyable: bool = False` prop on `webcompy.ui.code_block.CodeBlock` (enabled in documentation Markdown transforms) with clipboard copy feedback, and add opt-in clickable `#` anchor permalinks to Markdown document headings in `load_markdown_document()` / `prose.css` without polluting `MarkdownDocument.toc` labels.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `docs-site-documents`: Add payload (`resource_transfer="used"`) and style deduplication requirements, bounded scrollable sidebar/TOC/dropdown panels, client-side documentation search, `<html lang>` & ARIA landmarks/skip-link accessibility, `ThemeToggle` non-switch ARIA semantics, `DemoDisplay` heading order, `404` recovery layout, and UI doc demo placement.
- `docs-site-home`: Balance the Home feature-cards grid to avoid orphan slots and eliminate `.ui-card` margin interference with grid gaps.
- `code-block`: Add opt-in `copyable: bool = False` support on `CodeBlock` to copy raw code text to the clipboard while keeping `<pre><code>` token spans unchanged.
- `markdown-document`: Support opt-in clickable `#` heading anchor links in document mode (`load_markdown_document()` and `prose.css`) while keeping extracted `MarkdownDocument.toc` titles clean.

## Known Issues Addressed

- **`741 KB` HTML payload on `/` & duplicated `<style>` tags**: Switching `resource_transfer` from `"all-text"` (`1,258,977 B` decompressed / `520,057 B` compressed JSON) to `"used"` and consolidating ~80 copies of `DOCS_PAGE_SCOPED_STYLE` (`170,602 B`).
- **Unbounded sticky sidebars/TOC & `2,993px` dropdown**: Bounding `.docs-sidebar`, `.docs-toc`, and the Navbar dropdown so long navigation lists scroll independently within the viewport.
- **Accessibility & UX gaps**: Addressing missing `<html lang>`, missing `<nav aria-label>` & skip link, `<span class="navbar-brand">`, 3-state `role="switch"` ARIA violation, `DemoDisplay` `H1→H3` heading skip, bare uncontained `404`, and missing search/copy/permalink affordances.
- **Remaining tracked constraints**: Multi-app `ThemeManager` isolation and PyPI package availability noted in project Known Issues remain unchanged.

## Non-goals

- Core theme `color-scheme` / WCAG contrast fixes and Prose table overflow fixes (scoped to `fix/theme-contrast-and-prose-overflow`, Phase 1).
- Demo iframe theme synchronization and per-demo style/resize fixes (scoped to `fix/demo-iframe-theme-and-styles`, Phase 2).
- Full-text server-side search engine or indexing external runtime packages; search uses a lightweight client-side manifest/heading metadata index.

## Impact

- **Framework (`packages/webcompy`)**: `ui/code_block/_component.py`, `ui/_styles/code-block.css`, `template/_markdown_document.py`, `template/_markdown_transforms.py`, `ui/_styles/prose.css`.
- **Documentation app (`docs_app`)**: `webcompy_config.py`, `layout/__init__.py`, `layout/document.py`, `components/{navigation,docs_sidebar,docs_page,theme_toggle,demo_display,ui}.py`, `components/docs_search.py` (new), `templates/home.py`, `pages/not_found.py`, `documents/{ui_primitives,overlay,disclosure}.md`, `static/styles/components.css`.
- **Tests & specs**: Unit tests for `CodeBlock(copyable=True)` and heading anchors/TOC cleanliness, Playwright docs/a11y/search/copy E2E tests, SSG HTML payload size assertions, and `SPEC_INDEX.md` / `webcompy-review/SKILL.md` sync at archive time.
