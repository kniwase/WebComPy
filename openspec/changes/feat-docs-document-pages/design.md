# Design: feat-docs-document-pages

## Context

docs_app currently has: a top `Navbar` (no sidebar), a flat route table with `lazy()` components, a WIP stub at `/documents`, and one content page (`/documents/signal-stream`, a 188-line Python component template). Framework prerequisites are all merged:

- `load_markdown_document()` → `MarkdownDocument(content, metadata, toc)` with frontmatter (`---` flat / `+++` TOML), opt-in heading ids, `CodeBlock` replacement, and `prose.css` (`markdown-document` spec).
- Nested routes with shared layouts: a layout component renders a nested `RouterView()`; sibling navigation preserves the layout instance (`router` spec, RouterView depth/level reuse).
- `RouterLink` supports `active_class` / `exact` / `aria-current`, matching on path only.
- Scroll restoration never fires for non-router interactions; the router cannot express `#fragment` URLs at all.
- SSR title timing: `set_title` during setup reaches SSG `<title>` for all non-root paths (verified on HEAD), so every `/documents*` page is safe.

## Goals / Non-Goals

**Goals:**

- A documentation section with a persistent sectioned sidebar, per-page TOC, and Prev/Next — the standard three-column docs layout.
- One manifest drives routes, sidebar, Navbar dropdown, and Prev/Next so they cannot drift apart.
- Markdown pages authored as `.md` files with frontmatter; page components are ~10-line async wrappers.
- The existing signal-stream page joins the section without URL or content changes.

**Non-Goals:**

- Content authoring beyond Index / Installation / Quickstart.
- Search, versioning, i18n.
- Router fragment support (TOC uses plain anchors by design).
- Framework package changes.

## Decisions

### 1. Nested-route shared layout instead of flat routes + per-page layout

`/documents` becomes a parent route whose component is `DocsLayout`; pages become `children`. The layout renders the sidebar and a nested `RouterView()`.

- **Why**: sibling navigation preserves the layout instance (sidebar open/closed state survives page changes) per the RouterView level-reuse rule (route record + path_params + query identity). Route children are generated from the manifest, keeping "explicit routes" while avoiding a second hand-maintained route list.
- **Alternative rejected**: keep flat routes and wrap each page in a layout component — remounts the sidebar on every navigation and duplicates layout invocation in every page.

### 2. Manifest as single source of truth, with two page kinds

`docs_app/docs_manifest.py` defines:

```python
class DocsPageEntry(TypedDict, total=False):
    label: str        # nav label (required)
    path: str         # absolute route path (required)
    source: str       # Markdown resource path — Markdown page
    component: str    # "module:Attr" lazy reference — Python component page

class DocsSection(TypedDict):
    title: str
    pages: list[DocsPageEntry]

DOCS_SECTIONS: list[DocsSection] = [...]
```

Exactly one of `source` / `component` is set per entry. Route children, sidebar, Navbar "Documents" dropdown, and Prev/Next ordering all derive from `DOCS_SECTIONS`.

- **Why**: every consumer iterating one list guarantees consistency (Next.js explicitly documented the opposite failure mode — a manifest drifting from files — but here the manifest *is* the route definition, so drift is impossible by construction).
- Nav labels intentionally live in the manifest while page `<h1>`/`<title>` live in frontmatter: labels are often shorter than titles. A unit test asserts paths are unique, `source` files exist, and generated routes match the manifest — but does not force label==title.
- **Alternative rejected**: sidebar reads frontmatter titles at runtime by loading every `.md` — loads all documents on every page render and pollutes the hydration payload for marginal DRY benefit.

### 3. Page-side TOC, layout-side Prev/Next

- **TOC** lives in the page template (`docs_page_template(doc)`) because only the page has `doc.toc`. It renders an `<aside>` with plain `<a href="#id">` links. The aside is hidden when `toc` is empty (e.g. component pages like signal-stream don't render it at all).
- **Prev/Next** lives in `DocsLayout`: a `Computed` over the router's current path looks up neighbors in the flattened manifest order and renders footer links below the `RouterView`. Component pages get Prev/Next for free.
- **Why**: this split respects data ownership (child→parent data flow is intentionally avoided; no signal-passing or callbacks) while giving both page kinds consistent chrome.
- **Alternative rejected**: TOC in the layout populated via a shared signal written by the page — child→parent async write, fragile SSR timing, rejected for the same reasons as in `feat-markdown-document-support`.

### 4. TOC links are plain anchors, not RouterLinks

The router percent-encodes `#` in `to` and has no fragment concept; `HistoryPort` never treats hash changes as navigations. The docs_app HTML carries a `<base href="/">` tag (injected by the server), so a bare `href="#id"` would resolve against the root path and navigate away. TOC anchors therefore use an **absolute-path fragment** (`href="{current_path}#{id}"`, where `current_path` is the page's `RouterContext.path`) — a native same-document fragment navigation that works in browser, SSR HTML, and the static site, and cannot conflict with scroll restoration (no `navigate()` occurs).

- **Consequence**: heading ids from `load_markdown_document()` (Unicode-aware slugs) are the anchor contract; the TOC and content ids are guaranteed identical by `collect_headings`.
- Browser-native anchor jump does not scroll-margin for the fixed navbar; the shared page scoped style adds `scroll-margin-top` on `.prose :is(h1..h6)`.

### 5. Markdown page wrapper pattern

```python
@define_component
async def InstallationPage(context: ComponentContext[RouterContext]):
    doc = await load_markdown_document("documents/installation.md")
    context.set_title(f"{doc.metadata['title']} - WebComPy Docs")
    return docs_page_template(doc)
```

`docs_page_template(doc)` renders `<div class="docs-page">` containing `<article class="prose">doc.content</article>` and the TOC aside. Markdown files live in `docs_app/documents/` (inside the app package; the resource allow-list already covers `**/*.md`; SSR reads transfer via the hydration payload).

- Async setup is first-class (`async-component-setup` spec); SSR/SSG resolves it during the async rendering pipeline, and per investigation `set_title` lands in SSG `<title>` for all `/documents*` paths.

### 6. Signal-stream page migration (manifest `component` kind)

- Route moves from the flat table into the `/documents` children via manifest (`{"label": "Signal Stream", "path": "/documents/signal-stream", "component": "docs_app.pages.document.signal_stream:SignalStreamPage"}`), initially under a "Guides" section.
- **URL unchanged**, template untouched. The page renders inside `DocsLayout`; it has no TOC (its `Section` headings are `<h3>` without ids) and gains sidebar + Prev/Next.
- The Navbar "Documents" dropdown is populated from the manifest (replacing the hand-written single child).

### 7. Layout structure and responsiveness

Desktop grid: `sidebar | content(+TOC)`. Breakpoint behavior follows the existing Navbar mobile precedent: sidebar collapses behind a toggle; the TOC aside hides below the wide breakpoint (TOC is navigation sugar, content remains complete without it). Styles that target elements a component itself creates live in that component's `scoped_style` dict (`DocsLayout.scoped_style` for the grid shell and pager, `DocsSidebar.scoped_style` for the sidebar, and a shared `DOCS_PAGE_SCOPED_STYLE` on each Markdown page component for the article, TOC, and `.prose` heading `scroll-margin-top` — scoped CSS only matches the component that created the element, so the layout cannot style page-rendered content); `prose.css` is added to the app head link list in `app.py`.

### 8. Initial content scope

Three pages: `/documents` index (section cards, replaces the WIP stub), `getting-started/installation` (migrated from the home page's Get Started sections; home keeps its own copy — home is marketing, docs are reference), `getting-started/quickstart` (init → start → first component). Frontmatter uses flat `---` blocks (`title`, `description`).

## Risks / Trade-offs

- [Manifest grows stale vs. actual `.md` files or page modules] → Unit test `test_docs_manifest.py`: unique paths, `source` files exist on disk, `component` references import lazily, generated routes match manifest exactly.
- [Component pages lack TOC, inconsistent right column] → Accepted and spec'd: TOC aside renders only for Markdown pages with headings; content is complete without it.
- [Prev/Next on a remounted layout could flash stale links] → `Computed` over current path updates reactively; level reuse actually prevents remount on sibling navigation.
- [Index route `""` → `/documents` title timing] → Verified safe: `/documents` is non-root, so `set_title` reaches SSG HTML.
- [Sidebar toggle state shared across mobile navigation] → Layout instance reuse keeps it open after navigation; the toggle closes on link activation (same UX as the existing Navbar dropdowns).
- [prose.css link added globally affects other pages] → All rules are `.prose`-scoped and `@layer prose`; only docs content opts into the wrapper class.

## Migration Plan

Docs-site-only change. `/documents` and `/documents/signal-stream` URLs are preserved; new URLs are additive. Rollback = revert. E2E for `signal-stream` (`e2e/docs/test_documents.py` coverage) must pass unchanged against the moved route.

## Open Questions

None blocking. Whether "Guides" is the right home for signal-stream can be revisited when the content changes (③+) add real guide pages.
