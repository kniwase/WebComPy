# Proposal: feat-docs-document-pages

## Why

With `feat-markdown-document-support` merged, the framework can load Markdown documents with frontmatter, heading anchors, TOC extraction, code highlighting, and a `prose.css` preset. But docs_app's documentation section is still a "Work In Progress" stub at `/documents`, plus one flat-route page (`/documents/signal-stream`) with no shared structure. This change builds the actual documentation site section — layout, navigation, page scaffolding, and initial content — on top of that capability.

## What Changes

- Add a **documentation layout** (`DocsLayout`) as a nested-route shared layout under `/documents`: left sidebar with sectioned navigation (built from a manifest, `RouterLink` with `active_class`), a content grid, mobile-collapsible sidebar, and a Prev/Next footer computed reactively from the manifest and the current route.
- Add a **manifest** (`docs_app/docs_manifest.py`) as the single source of truth for the docs structure: sections, page order, paths, nav labels, and page backing (Markdown `source` or Python `component`). Route children, the sidebar, the Navbar "Documents" dropdown, and Prev/Next ordering are all generated from it.
- Add a **Markdown page template** (`docs_page_template(doc)`) rendering `<article class="prose">` content plus a right-hand TOC aside built from `doc.toc`, with plain `<a href="#id">` anchor links (no router involvement). Markdown page components are thin `async def` setups calling `load_markdown_document()` and `context.set_title(...)`.
- Migrate the existing **signal-stream page** into the layout via the manifest (URL `/documents/signal-stream` unchanged; template untouched).
- Replace the **WIP stub** with a real `/documents` index page (section cards), and add initial Markdown content: `installation` (migrated from the home page's Get Started sections) and `quickstart`.
- Load the opt-in **`prose.css`** preset in the app head.
- Add **E2E coverage** for the docs section (prod + static serving modes).

## Capabilities

### New Capabilities

- `docs-site-documents`: The docs_app documentation section — manifest schema and consistency rules, layout/sidebar/Prev-Next behavior, Markdown page template and TOC anchors, Navbar integration, and the signal-stream page relocation with URL preservation.

### Modified Capabilities

- `docs-e2e`: New E2E requirements for the documentation section (sidebar active state, TOC anchor navigation, titles, Prev/Next, Markdown rendering) in both prod and static serving modes.

## Impact

- **Code**: `docs_app/` — new `docs_manifest.py`, `layout/document.py` (DocsLayout), `components/docs_sidebar.py`, `components/docs_page.py` (page template + TOC), `pages/document/*.py` page wrappers, `documents/*.md` content; modifications to `router.py` (nested `/documents` tree), `layout.py` (Navbar dropdown from manifest), `app.py` (prose.css link)
- **Framework packages**: none — consumes the merged `load_markdown_document`, `prose.css`, nested routes, and `RouterLink` active state
- **Specs**: new `docs-site-documents`; delta to `docs-e2e`
- **Tests**: new unit tests (`tests/test_docs_manifest.py`), new route-specific E2E (`e2e/docs/test_installation.py`, `test_quickstart.py`, `test_signal_stream.py`, plus index-page coverage in `test_documents.py`)
- **URLs**: `/documents` and `/documents/signal-stream` preserved; new paths added. No breaking changes.

## Known Issues Addressed

None.

## Non-goals

- Full documentation content authoring (Core Concepts, Guides, API Reference) — later content changes; this change ships the structure plus three initial pages
- Docs search, version switching, i18n, "edit this page" links
- Router-level URL fragment support — TOC links intentionally use plain native anchors
- Converting the signal-stream page (or demo pages) to Markdown — it stays a Python component page
- Changes to framework packages (`packages/`) or the Markdown rendering pipeline
