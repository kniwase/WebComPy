# Tasks

## 1. Static HTML Payload & Style Deduplication

- [ ] 1.1 Switch `resource_transfer` in `docs_app/webcompy_config.py` from `"all-text"` to `"used"` and verify `uv run python -m webcompy generate` significantly reduces `docs/index.html` `__webcompy_data__` payload while client-side docs navigation continues loading Markdown routes cleanly.
- [ ] 1.2 Deduplicate `DOCS_PAGE_SCOPED_STYLE` across ~80 lazy page modules by moving shared docs page CSS rules into `docs_app/static/styles/components.css` (or a single layout-owned style block); verify rendered `<head>` contains only one copy of docs page CSS in unit and E2E tests.

## 2. Reader Ergonomics: Copyable CodeBlock & Heading Anchors

- [ ] 2.1 Add opt-in `copyable: bool = False` prop to `webcompy.ui.code_block.CodeBlock` (`packages/webcompy/src/webcompy/ui/code_block/_component.py`) and corresponding button styles under `@layer components` in `code-block.css`, keeping default (`copyable=False`) output and direct `<code>` token-span children unchanged; add unit tests covering both modes.
- [ ] 2.2 Add opt-in clickable `#` heading anchor insertion in `packages/webcompy/src/webcompy/template/_markdown_transforms.py` and `load_markdown_document()`, ensuring `collect_headings()` runs before anchor insertion (or excludes `.heading-anchor`) so `MarkdownDocument.toc` stays `#`-free, and add `.heading-anchor` styling in `prose.css`; verify with unit tests.
- [ ] 2.3 Enable copyable code blocks and heading anchors in `docs_app` Markdown document loading and add CSS spacing support in `.prose`; verify visually and functionally in Playwright docs E2E tests.

## 3. Navigation, Scroll Bounds & Client-Side Search

- [ ] 3.1 Add viewport-relative `max-height` and independent `overflow-y: auto` scrolling to sticky `.docs-sidebar` and `.docs-toc`, and group the Navbar `Documents` dropdown by manifest section inside a scrollable bounded panel (`docs_app/components/navigation.py`, `docs_app/layout/document.py`, `docs_app/components/docs_page.py`, `docs_app/static/styles/components.css`); verify on long pages like `/documents/api/server-and-cli/`.
- [ ] 3.2 Implement `DocsSearch` (`docs_app/components/docs_search.py`) driven by `DOCS_SECTIONS` metadata and wire it into the Navbar/docs header with keyboard shortcut focus and direct router navigation; verify search filtering and navigation in Playwright tests.

## 4. Accessibility & Page Layout Polish

- [ ] 4.1 Set `<html lang="en">` in `DocsRoot`, add a skip-to-content link and `#main-content` landmark target, label all `<nav>` landmarks (`aria-label`), convert `.navbar-brand` into a `RouterLink` to `/`, and update `ThemeToggle` (`docs_app/components/theme_toggle.py`) to an accessible SVG cycle button without `role="switch"`; verify landmark/ARIA assertions in unit and Playwright checks.
- [ ] 4.2 Update `DemoDisplay` heading level to `H2` (`docs_app/components/demo_display.py`), move live demo sections before `Next steps` in `ui_primitives`, `overlay`, and `disclosure` docs, balance Home feature cards and eliminate `.ui-card` grid margin interference (`docs_app/templates/home.py`, `docs_app/static/styles/components.css`), and add structured recovery layout/links to `docs_app/pages/not_found.py`; verify in Playwright across mobile and desktop viewports.

## 5. Verification & Spec Sync

- [ ] 5.1 Run local CI checks (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/`, `uv run python -m webcompy generate`, and `scripts/run-e2e-tests.sh`) and inspect generated `docs/index.html` size and accessibility tree.
- [ ] 5.2 Before archiving, sync delta specs into `openspec/specs/` and update `openspec/SPEC_INDEX.md` and `.agents/skills/webcompy-review/SKILL.md` (`python3 scripts/check-doc-spec-refs.py`).
