# Proposal

## Why

A comprehensive Playwright audit of the live site (`https://www.webcompy.net/`) across 81 routes, 5 viewport sizes, and all four OS/site theme combinations revealed systematic WCAG 2.1 AA contrast failures (down to `1.03:1`), severe horizontal layout overflow in Markdown tables and inline code blocks that collide with the right-hand TOC and force horizontal scroll on mobile/tablet, broken modal/drawer backdrops in dark mode, visible `.py-error` hydration-warning banners in the DOM on reload and 404 routes, and an `AttributeError` in `BrowserHistoryPort` when handling `history.state` during `popstate` navigation.

## What Changes

- **Explicit `color-scheme` & base control theming (`theme-system`, `design-tokens`)**: Emit `color-scheme: light` for `Theme.LIGHT` and `color-scheme: dark` for `Theme.DARK` in `ThemeManager` CSS output, define the missing `--shadow-lg` design token in both `tokens.css` and `_tokens.py`, introduce `--color-on-accent` / adjust `--color-accent` (dark mode `#1f6feb`) and `--tok-comment` (light mode `>= 4.5:1`) to satisfy WCAG 2.1 AA contrast, and add tokenized base styling for native form controls (`<button>`, `<input>`, `<select>`, `<textarea>`) in framework base styles so OS vs. site theme inversions remain readable.
- **Dark-mode & layout fixes for overlay primitives (`ui-overlay`)**: Fix `.webcompy-modal-backdrop` so it uses a translucent dark overlay rather than `var(--color-fg)` with opacity, ensure `--shadow-lg` resolves, add padding, backdrop support, and surface contrast to `.webcompy-drawer`, and ensure close button contrast across themes.
- **Markdown table & inline-code overflow protection (`markdown-document`, `docs-site-documents`)**: Wrap rendered Markdown `<table>` elements in a `.prose-table-wrapper` container inside `load_markdown_document()`'s document transform pass (keeping `render_markdown()` and `markdown-conformance` intact), add responsive overflow rules (`overflow-x: auto`, `overflow-wrap: anywhere` / `word-break` on long inline `<code>` and media) in `prose.css`, and apply `minmax(0, 1fr)` / `min-width: 0` grid constraints on `.docs-layout` / `.docs-content` so content never overlaps the TOC or causes document-level horizontal scrolling.
- **Hydration noise, cookie toggle sync, 404 alignment, and history state safety (`theme-system`, `async-rendering`, `docs-site-documents`, `browser-api`)**: Route `emit_report_summary()` warnings through `webcompy.logging.warn` (`console.warn`) instead of stdlib `logging` (eliminating `<div class="py-error">` banners from stderr), eliminate the reload `ThemeToggle` and static `404.html` catch-all hydration mismatches, and fix `BrowserHistoryPort._on_popstate` / `refresh_from_window` to convert Pyodide `JsProxy` `history.state` safely without calling `.to_dict()`.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `theme-system`: Emit explicit `color-scheme` declarations per active `Theme` variant (`light`, `dark`, `system`) and synchronize cookie-persisted theme hydration in statically generated apps without spurious UI mismatches.
- `design-tokens`: Reconcile token stylesheet delivery with `ThemeManager`, add `--shadow-lg` and accent-contrast tokens, declare explicit `color-scheme` behavior and native form-control token defaults, and raise light/dark color tokens to WCAG 2.1 AA contrast.
- `ui-overlay`: Ensure Modal and Drawer backdrops, surfaces, padding, close-button contrast, and `--shadow-lg` elevation render legibly in both light and dark modes.
- `markdown-document`: Wrap document-rendered tables in `.prose-table-wrapper` inside `load_markdown_document()` and update `prose.css` to prevent table, inline-code, and media horizontal overflow.
- `async-rendering`: Route hydration mismatch summary warnings solely to browser `console.warn` (never DOM `.py-error` stderr banners) and prevent false-positive mismatches from static catch-all 404 or theme-cookie hydration.
- `docs-site-documents`: Enforce zero horizontal overflow and zero TOC overlap across mobile, tablet, and desktop breakpoints via `minmax(0, 1fr)` / `min-width: 0` grid tracks and responsive table handling, plus mismatch-free `ThemeToggle` and 404 hydration.
- `browser-api`: Fix `BrowserHistoryPort` JavaScript `history.state` conversion during `popstate` and window refresh so `JsProxy` values do not raise `AttributeError: to_dict`.

## Known Issues Addressed

- **Theme contrast on OS/site inversion & dark mode**: Resolving the discrepancy where `Theme.LIGHT` emitted empty CSS (leaving `color-scheme: light dark` bound to an OS dark preference) and where `--color-accent` (`3.10:1` on dark) and `--tok-comment` (`4.27:1` on light) failed WCAG AA.
- **Undefined `--shadow-lg` & inverted overlay backdrop**: Fixing `primitives.css` references to an undefined `--shadow-lg` token and `background: var(--color-fg)` on `.webcompy-modal-backdrop`.
- **Prose overflow on narrow and desktop viewports**: Containing the 7 overflowing tables at `1440px` and 60 overflowing tables + 24 overflowing inline code spans at `390px`, plus eliminating `.docs-toc` collision at `1100px`–`1280px`.
- **Visible `.py-error` hydration banner & `404`/`ThemeToggle` mismatches**: Fixing `emit_report_summary()` stdlib logger usage alongside `ThemeToggle` and `404` catch-all hydration alignment.
- **`BrowserHistoryPort` `history.state` `AttributeError`**: Replacing `.to_dict()` calls on `window.history.state` `JsProxy` objects with proper PyScript FFI conversion (`to_py()`).
- **Remaining tracked router known issue**: Explicit listener/proxy disposal refactoring replacing `BrowserHistoryPort.__del__` remains out of scope and continues to be tracked separately in OpenSpec Known Issues.

## Non-goals

- Synchronizing theme preferences or repairing contrast/scoped styles inside isolated demo iframes (`docs_app/static/_demos/`), which is scoped to `fix/demo-iframe-theme-and-styles` (Phase 2).
- Navigation chrome redesign, sidebar/TOC independent scrolling, copy-to-clipboard buttons, clickable heading anchors, client-side search, `<html lang>`, or SSG payload/style deduplication, which are scoped to `feat/docs-ux-a11y-and-payload` (Phase 3).
- Modifying raw `render_markdown()` block parsing or changing `markdown-conformance` CommonMark/GFM outputs.
- Refactoring `BrowserHistoryPort.__del__` listener/proxy teardown beyond safe `history.state` conversion.

## Impact

- **Core framework (`packages/webcompy`)**: `ui/theme/_manager.py`, `ui/theme/_tokens.py`, `ui/_styles/{tokens.css,reset.css,primitives.css,prose.css,components.css}`, `template/_markdown_document.py`, `template/_markdown_transforms.py`, `hydration/_report.py`, `ports/_browser/_history.py`.
- **Documentation app (`docs_app`)**: `layout/__init__.py` / `components/theme_toggle.py`, `docs_app/static/styles/components.css`, `docs_app/pages/not_found.py`.
- **Tests & specs**: Unit tests (contrast/token parity, Markdown wrapper, hydration logging, history FFI proxy conversion), Playwright docs E2E overflow/theme checks, and spec sync updates in `openspec/SPEC_INDEX.md` and `.agents/skills/webcompy-review/SKILL.md`.
