# Design

## Context

The live-site audit revealed three groups of structural improvements that sit above individual theme/table bugfixes (see `proposal.md`):

1. **SSG payload & `<style>` bloat**: `docs_app/webcompy_config.py` sets `resource_transfer="all-text"`, embedding `1,258,977 B` decompressed (`520,057 B` compressed) of all 81 Markdown sources inside every HTML page's `__webcompy_data__` script, alongside ~80 duplicated copies of `DOCS_PAGE_SCOPED_STYLE` (`170,602 B` of `<style data-webcompy-cid>` elements) emitted into `<head>` because `ComponentGenerator` registers scoped styles per page wrapper component. Together these bloat `/` HTML to `741 KB`.
2. **Navigation, sticky bounds, search, and reader ergonomics**: Sticky `.docs-sidebar` (`3,465px`) and `.docs-toc` (`4,690px` on `server-and-cli`) lack `max-height` / `overflow-y: auto`; the Navbar `Documents` dropdown renders 80 flat links (`2,993px`); there is no client-side search across the 80 pages; `CodeBlock` has no copy button; and Markdown headings expose no clickable `#` permalink.
3. **Accessibility & layout polish**: Missing `<html lang="en">`, skip link, `<nav aria-label>` landmarks; `<span class="navbar-brand">`; misapplied `role="switch"` on the 3-state `ThemeToggle` (`"🖥"` emoji); `DemoDisplay` `H1 -> H3` heading jump; Home landing 5-card grid orphan slot compounded by `.ui-card` margin; bare uncontained `404` page; and live UI component demos on `ui-primitives`, `overlay`, and `disclosure` placed below `Next steps`.

## Goals / Non-Goals

**Goals:**
- Reduce initial static HTML size substantially via `resource_transfer="used"` and single-copy shared docs page CSS.
- Improve documentation findability and long-page ergonomics (bounded scrolling sidebars/TOC, grouped Navbar dropdown, client-side search, copyable `CodeBlock`, clickable heading `#` anchors).
- Achieve clean WCAG/ARIA structural semantics (`lang`, landmarks, skip link, non-switch theme control, heading hierarchy, balanced Home grid, recovery `404`).

**Non-Goals:**
- Changing Phase 1 theme/contrast tokens or table-overflow containment (`fix/theme-contrast-and-prose-overflow`).
- Changing Phase 2 demo iframe theme syncing or per-demo scoped CSS (`fix/demo-iframe-theme-and-styles`).
- Server-side search indexing or external JS libraries (e.g., Lunr/Algolia).

## Decisions

### 1. Payload Reduction (`resource_transfer="used"`) & Shared Docs Page CSS
- **Decision**:
  - Change `docs_app/webcompy_config.py` `resource_transfer` from `"all-text"` to `"used"`. Because `ServerResourcePort` already records only files awaited during each route's SSR pass, each static page embeds only its own Markdown resource (instant flicker-free hydration) while client-side navigation fetches target Markdown resources on demand (`ResourcePort` client fallback to `/_webcompy-resources/...` and `preload` for likely next routes if desired).
  - Remove duplicated `scoped_style` definitions from per-page dynamic generators or replace per-page `DOCS_PAGE_SCOPED_STYLE` duplication with shared rules in `docs_app/static/styles/components.css` (plus/or a single `DocsPageView` shared component mounted once inside `docs_page_template`), reducing ~80 `<style>` tags (`170 KB`) to one shared stylesheet.
- **Alternatives rejected**: Manually stripping `<style>` tags in post-build HTML hacks (fragile and unnecessary once CSS lives in a shared stylesheet / single component).

### 2. Bounded Sidebars, Grouped Dropdown, and Pure-Python Client Search
- **Decision**:
  - Give `.docs-sidebar` and `.docs-toc` `position: sticky; top: var(--docs-header-offset); max-height: calc(100vh - var(--docs-header-offset) - 1rem); overflow-y: auto; overscroll-behavior: contain;`.
  - Render the Navbar `Documents` dropdown from `DOCS_SECTIONS` grouped by category headers inside a container with `max-height: min(70vh, 520px); overflow-y: auto;`.
  - Add a `DocsSearch` component (`docs_app/components/docs_search.py`) mounted in the Navbar/docs header: an accessible search trigger button (`/` or `Ctrl+K` hint) opening a modal/panel (`webcompy.ui.Modal` or lightweight reactive overlay) filtering a static Python tuple derived from `DOCS_SECTIONS` (`title`, `section`, `group`, `path`, summary/keywords) via `Reactive[str]` query and `Computed` matches, navigating cleanly via `Router`.
- **Rationale**: Zero new JS dependencies, works identically in dev/prod SSR and static exports, and avoids fetching all 80 Markdown files just to search titles/topics.

### 3. Copyable `CodeBlock` & Heading `#` Anchors (Ordering Constraint!)
- **Decision**:
  - **`CodeBlock(copyable: bool = False)`**: In `packages/webcompy/src/webcompy/ui/code_block/_component.py`, wrap the `<pre><code class="language-{lang}">...</code></pre>` block in a `<div class="code-block-container">` **only when `copyable=True`** (keeping existing `<pre><code...>` structure untouched when `copyable=False`). Render `<button type="button" class="code-block-copy" aria-label="Copy code">` wired to `window.navigator.clipboard.writeText(current_code)` with a 1.5s `Copied` state via a signal. Style cleanly inside `code-block.css` under `@layer components`. Enable `copyable=True` in `load_markdown_document()`'s `replace_code_blocks` transform (opt-in / configurable via kwarg) so all docs code blocks get copy buttons.
  - **Heading `#` anchors & `collect_headings` ordering**: In `packages/webcompy/src/webcompy/template/_markdown_document.py` / `_markdown_transforms.py`, ensure `collect_headings()` runs **before** inserting `<a class="heading-anchor" href="#{id}" aria-hidden="true">#</a>` (AND/OR teach `collect_headings()` to skip `.heading-anchor` elements), so `MarkdownDocument.toc` entries remain clean (`"Reactive Signals"`, NOT `"Reactive Signals#"`). In `prose.css` (`@layer prose`), reveal `.heading-anchor` on heading hover/focus-within with accessible focus styling.

### 4. Accessibility, Landmarks, Heading Levels, & Layout Polish
- **Decision**:
  - Call `context.set_html_attr("lang", "en")` in `DocsRoot` (`docs_app/layout/__init__.py`) — leveraging `_html.py`'s existing `ctx._root.html_attrs` support cleanly.
  - Add a visually-hidden-until-focused `<a class="skip-link" href="#main-content">Skip to main content</a>` as the first focusable item in `DocsRoot`, paired with `id="main-content"` on `<main>`.
  - Add distinct `aria-label` values to Navbar (`"Primary navigation"`), sidebar (`"Documentation navigation"`), TOC (`"Table of contents"`), and footer pagination (`"Page navigation"`), and convert `<span class="navbar-brand">` into a `RouterLink` pointing to `"/"`.
  - Refactor `docs_app/components/theme_toggle.py` from `role="switch"`/`aria-checked` (which violates ARIA for 3 mutually exclusive choices) to a clean cycle `<button type="button">` with an inline SVG sun/moon/monitor icon and dynamic `aria-label` (e.g., `"Theme: System (click to switch to Light)"`).
  - Change `DemoDisplay`'s wrapper heading (`docs_app/components/demo_display.py`) from `H3` to `H2` (or configurable `heading_level`, defaulting to `"h2"`) so documentation pages avoid `H1 -> H3` skips.
  - Update `docs_app/templates/home.py` feature cards (either a symmetric 4-card or 6-card grid / balanced 3-col layout on desktop, 2-col tablet, 1-col mobile) and scope/remove `.ui-card` vertical margin inside `.features-grid` so grid gaps match cleanly.
  - Polish `docs_app/pages/not_found.py` with centered container card styling and `RouterLink` buttons to `/` and `/documents/getting-started/what-is-webcompy`.
  - Update `ui_primitives.md`, `overlay.md`, `disclosure.md` (or their corresponding page templates) so live interactive component demos appear before `"Next steps"`.

## Risks / Trade-offs

- [Client-side route transitions without pre-baked `"all-text"` payload add one HTTP fetch per new visited docs page] → `ResourcePort.load_text` already caches fetched Markdown in memory across revisits, and switching to `"used"` eliminates ~500 KB of dead JSON on initial load.
- [Clipboard API (`navigator.clipboard.writeText`) requires secure context (`https:` or `localhost`)] → Guard copy click handler gracefully in `try/except` with fallback logging if unavailable in constrained test contexts.
- [Adding `<div class="code-block-container">` wrapper when `copyable=True` affects CSS selectors matching direct `> pre`] → Preserve direct `<pre>` structure when `copyable=False` (default), update `prose.css` (`.prose .code-block-container`), and keep `<span class="tok-*">` direct children of `<code>` invariant intact.
