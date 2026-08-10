# Tasks: feat-docs-document-pages

## 1. Manifest

- [x] 1.1 Create `docs_app/docs_manifest.py` with `DocsPageEntry` / `DocsSection` TypedDicts, `DOCS_SECTIONS` (Getting Started: Installation, Quickstart; Guides: Signal Stream), validation of exactly-one-of `source`/`component`, and helpers: `flatten_pages()` (ordered page list), `route_children()` (lazy route children), `prev_next(path)` lookup
- [x] 1.2 Add `tests/test_docs_manifest.py`: unique paths, exactly-one-of validation errors, `source` files exist, `component` references importable, route children match manifest, prev/next ordering and boundary omissions

## 2. Layout and Components

- [x] 2.1 Create `docs_app/layout/document.py` (`DocsLayout`): sidebar slot area, nested `RouterView`, reactive Prev/Next footer from manifest, mobile sidebar toggle, `DocsLayout.scoped_style` (grid, sticky sidebar, breakpoints, `scroll-margin-top` for headings)
- [x] 2.2 Create `docs_app/components/docs_sidebar.py`: sectioned nav from manifest using `RouterLink` with `active_class` and `aria-current`, collapsible sections, mobile behavior
- [x] 2.3 Create `docs_app/components/docs_page.py`: `docs_page_template(doc)` rendering `<article class="prose">` + TOC aside (plain `<a href="#id">`, hidden when toc empty)
- [x] 2.4 Wire `prose.css` into `docs_app/app.py` head links

## 3. Pages and Routing

- [x] 3.1 Restructure `docs_app/router.py`: `/documents` parent with `DocsLayout`, children from `route_children()`; remove the flat `/documents/signal-stream` entry (URL preserved via manifest)
- [x] 3.2 Replace `docs_app/pages/document/home.py` stub with a real Index page (section cards from manifest)
- [x] 3.3 Create Markdown page wrappers `docs_app/pages/document/installation.py` and `quickstart.py` (async setup + `load_markdown_document` + `set_title` + `docs_page_template`)
- [x] 3.4 Update `docs_app/layout.py` Navbar "Documents" dropdown to populate from the manifest

## 4. Initial Content

- [x] 4.1 Write `docs_app/documents/installation.md` (flat frontmatter `title`/`description`; migrate and organize the home page's uv/Poetry Get Started content)
- [x] 4.2 Write `docs_app/documents/quickstart.md` (init → dev server → first component, concise)

## 5. Tests

- [x] 5.1 Add `e2e/docs/test_document_pages.py` following the `docs_page_on` fixture pattern: titles, sidebar active state, TOC anchor jump, code block highlighting, Prev/Next navigation (prod + static modes)
- [x] 5.2 Verify existing `e2e/docs/test_documents.py` and signal-stream E2E still pass against the moved route

## 6. Verification

- [x] 6.1 Run `uv run ruff check .` and `uv run ruff format --check .`
- [x] 6.2 Run `uv run pyright`
- [x] 6.3 Run `uv run python -m pytest tests/ --tb=short`
- [x] 6.4 Run `uv run python -m webcompy generate` on docs_app and inspect generated `/documents*` HTML (titles, prose.css link, heading ids)
- [x] 6.5 Run `scripts/run-e2e-tests.sh` docs groups
- [x] 6.6 Update `AGENTS.md` File → Spec Mapping (docs_app row) and Current Specs list (`docs-site-documents`); sync `.opencode/skills/webcompy-review/SKILL.md` references; run `python3 scripts/check-doc-spec-refs.py`
- [x] 6.7 Run `openspec validate feat-docs-document-pages`
