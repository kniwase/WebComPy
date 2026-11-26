# Tasks

## 1. Theme System & Design Tokens

- [ ] 1.1 Update `ThemeManager._build_theme_css()` in `packages/webcompy/src/webcompy/ui/theme/_manager.py` to emit explicit `color-scheme: light` for `Theme.LIGHT` and `color-scheme: dark` for `Theme.DARK` alongside `DARK_TOKENS`, keeping `Theme.SYSTEM` media-query behavior; verify with unit tests under `tests/`.
- [ ] 1.2 Add `--shadow-lg` and `--color-on-accent`, adjust dark `--color-accent` (`#1f6feb`) and light `--tok-comment` (`>= 4.5:1`) in both `packages/webcompy/src/webcompy/ui/_styles/tokens.css` and `packages/webcompy/src/webcompy/ui/theme/_tokens.py`; add unit test asserting token parity and WCAG 2.1 AA contrast ratios (`>= 4.5:1`).
- [ ] 1.3 Add low-specificity `@layer reset` defaults for native form controls (`button`, `input`, `select`, `textarea`) in `packages/webcompy/src/webcompy/ui/_styles/reset.css` / `primitives.css` inheriting active `color-scheme` and tokenized surface/text/border colors; verify in unit/E2E tests across all 4 OS/site theme combinations.

## 2. Overlay Contrast & Backdrop

- [ ] 2.1 Fix `.webcompy-modal-backdrop` and add `.webcompy-drawer-backdrop` in `packages/webcompy/src/webcompy/ui/_styles/primitives.css` using dark translucent scrim (`rgba(0, 0, 0, 0.5)`) instead of `var(--color-fg)` opacity, add internal padding, surface tokens, `--shadow-lg`, and close-control contrast to Modal and Drawer; update Python component wrappers in `webcompy/ui/` if Drawer backdrop element is emitted, and verify rendered styles in `tests/` and Playwright overlay E2E tests.

## 3. Markdown Document Wrapping & Responsive Prose Layout

- [ ] 3.1 Add a `wrap_tables` transform in `packages/webcompy/src/webcompy/template/_markdown_transforms.py` and enable it by default in `load_markdown_document()` (`_markdown_document.py`) to wrap `<table>` in `<div class="prose-table-wrapper">`; verify `tests/` cover wrapped document tables while raw `render_markdown()` and `markdown-conformance` remain untouched.
- [ ] 3.2 Update `packages/webcompy/src/webcompy/ui/_styles/prose.css` (inside `@layer prose`) with `.prose .prose-table-wrapper` horizontal scroll rules, `.prose :not(pre) > code` `overflow-wrap: anywhere`, heading/paragraph word-break protection, and responsive `img` `max-width: 100%`; verify via unit assertions on stylesheet output.
- [ ] 3.3 Update grid columns to `minmax(0, 1fr)` and add `min-width: 0` on `.docs-main`, `.docs-content`, and `.prose` in `docs_app/layout/document.py` and `docs_app/components/docs_page.py`; verify via Playwright docs E2E that `scrollWidth <= clientWidth` and zero TOC overlap hold across `390px`, `1024px`, `1100px`, `1280px`, and `1440px`.

## 4. Hydration Warnings, 404/Cookie Mismatches & History FFI

- [ ] 4.1 Replace stdlib logger usage in `packages/webcompy/src/webcompy/hydration/_report.py` (`emit_report_summary`) with `webcompy.logging.warn` so mismatch summaries log to `window.console.warn` instead of stderr `.py-error` DOM banners; verify with unit tests and browser tests.
- [ ] 4.2 Resolve static-site `ThemeToggle` cookie reload hydration mismatches and `docs_app/pages/not_found.py` catch-all `404` hydration mismatches; verify in browser Playwright checks that theme reload and unknown-URL navigation report zero hydration mismatches and zero `.py-error` elements.
- [ ] 4.3 Replace `hist_state.to_dict()` in `packages/webcompy/src/webcompy/ports/_browser/_history.py` (`_on_popstate` and `refresh_from_window`) with safe PyScript FFI (`to_py()` + `isinstance(..., dict)`) conversion; add unit/browser tests covering non-null `JsProxy` history state on `popstate`.

## 5. Verification & Spec Sync

- [ ] 5.1 Run full local checks (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/`, `scripts/run-browser-tests.sh --probes`, docs E2E tests via `scripts/run-e2e-tests.sh`) and confirm zero errors or horizontal/contrast regressions.
- [ ] 5.2 Before archiving, sync delta specs into `openspec/specs/` and update `openspec/SPEC_INDEX.md` and `.agents/skills/webcompy-review/SKILL.md` (`python3 scripts/check-doc-spec-refs.py`).
