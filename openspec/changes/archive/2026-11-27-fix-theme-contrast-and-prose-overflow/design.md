# Design

## Context

The production browser audit of `https://www.webcompy.net/` surfaced several interconnected framework and docs-site bugs (see `proposal.md` for full scope and counts):

1. **Theme polarity vs. OS preference mismatch**: `tokens.css` declares `color-scheme: light dark` on `:root`. In `webcompy/ui/theme/_manager.py`, `ThemeManager._build_theme_css()` returns `""` for `Theme.LIGHT`, `:root { ... }` dark tokens without `color-scheme: dark` for `Theme.DARK`, and `@media (prefers-color-scheme: dark)` for `Theme.SYSTEM`. Consequently, inverting OS vs. site polarity leaves browser default form controls (`<button>`, `<input>`) painted in OS polarity while text tokens follow site polarity (`1.03:1`–`2.96:1`).
2. **Token & overlay deficiencies**: `--shadow-lg` is used in `primitives.css` (`Modal`, `Drawer`) and `components.css`, yet undefined in `tokens.css` and `_tokens.py`. Light `--tok-comment` (`#6e7781` on `#f6f8fa` = `4.27:1`) and dark `--color-accent` (`#4493f8` with `#ffffff` = `3.10:1`) fail WCAG 2.1 AA (`4.5:1`). `.webcompy-modal-backdrop` sets `background: var(--color-fg); opacity: 0.4`, washing out dark mode instead of dimming, and `.webcompy-drawer` lacks padding and a backdrop.
3. **Prose overflow**: `.docs-layout` and `.docs-content` lack `min-width: 0` / `minmax(0, 1fr)`, and rendered GFM `<table>` elements and long inline `<code>` spans lack overflow containment in `prose.css`, causing tables to expand past `.prose`, overlap sticky `.docs-toc` at `1100px`–`1280px`, and scroll horizontally on `390px` mobile. Meanwhile `render_markdown()` itself must preserve 654/672 `markdown-conformance` behavior.
4. **Hydration banners, mismatches, and history `JsProxy`**: `hydration/_report.py` calls Python stdlib `_logger.warning(...)` which hits PyScript stderr and renders a visible `<div class="py-error">` banner in the DOM. Static exports bake `Theme.SYSTEM` into HTML while clients with a `webcompy-theme` cookie hydrate `ThemeToggle` with dark/light labels (`attribute=2, text=1`), and catch-all `404.html` renders a differing path (`NotFound` mismatch). Finally, `BrowserHistoryPort._on_popstate` and `refresh_from_window` call `hist_state.to_dict()` on Pyodide `JsProxy`, raising `AttributeError`.

## Goals / Non-Goals

**Goals:**
- Enforce `color-scheme` alignment and WCAG 2.1 AA contrast across all 4 OS/site theme combinations, tokens, form controls, and overlays.
- Eliminate document horizontal overflow and TOC collision across all 81 routes and all audited viewports (`390px`–`1440px`) without altering `markdown-conformance`.
- Route hydration warnings strictly to `window.console.warn` (`webcompy.logging.warn`) and achieve zero hydration mismatches on theme-cookie reload and static 404.
- Fix Pyodide `JsProxy` history state conversion on browser Back/Forward navigation.

**Non-Goals:**
- Demo iframe CSS/theme sync (deferred to Phase 2).
- Navigation redesign, client-side search, heading anchors, code copy button, `<html lang>`, or SSG payload deduplication (deferred to Phase 3).
- Refactoring `BrowserHistoryPort.__del__` proxy lifecycle disposal.

## Decisions

### 1. Explicit `color-scheme` in `ThemeManager._build_theme_css()` + Base Control Rules
- **Decision**: Have `_build_theme_css()` emit `:root {\n  color-scheme: light;\n}` for `Theme.LIGHT`, `:root {\n  color-scheme: dark;\n  ...\n}` for `Theme.DARK`, and `@media (prefers-color-scheme: dark) {\n  :root {\n    color-scheme: dark;\n    ...\n  }\n}` for `Theme.SYSTEM` (keeping base `color-scheme: light dark` in `tokens.css`). Additionally, add low-specificity rules in `@layer reset` (`reset.css` / `primitives.css`) giving `button, input, select, textarea` tokenized defaults (`background: var(--color-bg-card); color: var(--color-fg); border: 1px solid var(--color-border); color-scheme: inherit;`) while keeping consumer and utility overrides intact.
- **Rationale**: Setting `color-scheme` inside `<style data-webcompy-dynamic>` honors the `theme-system` invariant that dynamic CSS injection is the single source of truth (no `data-theme` attribute). Giving unstyled controls tokenized colors + `color-scheme` guarantees contrast even on Safari/Chromium UA buttons/inputs.
- **Alternatives rejected**: Adding `data-theme="dark|light"` attributes on `<html>` (violates `theme-system` spec).

### 2. Contrast & Token Additions (`tokens.css` & `_tokens.py`)
- **Decision**:
  - Add `--shadow-lg` in light and dark token sets (keeping `tokens.css` and `webcompy/ui/theme/_tokens.py` synchronized and verified by unit tests).
  - Add `--color-on-accent: #ffffff` and tune dark `--color-accent` from `#4493f8` (`3.10:1` with white) to GitHub's accessible solid accent `#1f6feb` (`>= 4.5:1` with `#ffffff`), reserving `#4493f8` / `#58a6ff` for `--color-link`.
  - Darken light `--tok-comment` from `#6e7781` (`4.27:1` on `#f6f8fa`) to `#57606a` or `#59636e` (`>= 5.0:1` on `#f6f8fa`).
  - Update `.webcompy-modal-backdrop` and add a matching `.webcompy-drawer-backdrop` using `background: rgba(0, 0, 0, 0.5)` instead of `background: var(--color-fg); opacity: 0.4`. Give `.webcompy-drawer` panel `padding`, border, `background: var(--color-bg-elevated)`, `color: var(--color-fg)`, `box-shadow: var(--shadow-lg)`, and accessible close button styles.
- **Alternatives considered**: Keeping `#4493f8` as button background and switching `--color-on-accent` in dark mode to `#0d1117`. Using `#1f6feb` keeps white button text crisp and consistent with GitHub's dark primary CTA; both options hit WCAG AA, and tokenizing `--color-on-accent` allows future adjustment cleanly.

### 3. Document-Only Table Wrapping & Grid Overflow Containment
- **Decision**:
  - In `webcompy/template/_markdown_transforms.py` (invoked by `load_markdown_document()`, not `render_markdown()`), add a `wrap_tables` transform (default `True`, overridable via kwarg) that wraps each `Element("table", ...)` subtree in `Element("div", {"class": "prose-table-wrapper"}, table)`.
  - In `webcompy/ui/_styles/prose.css` (within `@layer prose`), style `.prose .prose-table-wrapper { overflow-x: auto; max-width: 100%; margin: var(--space-4) 0; }` with inner `table { margin: 0; }`, add `.prose :not(pre) > code { overflow-wrap: anywhere; }`, `.prose h1, .prose h2, .prose h3, .prose p, .prose li { overflow-wrap: break-word; }`, and `.prose img { max-width: 100%; height: auto; }`. Also add defensive `max-width: 100%; overflow-x: auto;` fallback styling when `.prose table` appears unwrapped.
  - In `docs_app/components/docs_page.py` (`DOCS_PAGE_SCOPED_STYLE`) and `docs_app/layout/document.py`, update grid column tracks from `1fr` to `minmax(0, 1fr)` and add `min-width: 0` on `.docs-main`, `.docs-content`, and `.prose` so intrinsic `table`/`pre` minimum widths never blow out grid columns or invade `.docs-toc`.
- **Rationale**: Keeps `markdown-conformance` (raw `render_markdown()`) unchanged while making all long-form Markdown tables horizontally scrollable within their column.
- **Alternatives rejected**: Modifying `_markdown_blocks.py` table emission globally (would break raw `render_markdown()` expectations and `markdown-conformance` snapshots).

### 4. Eliminating Hydration `.py-error` Banners, Reload/404 Mismatches, and `JsProxy.to_dict()`
- **Decision**:
  - **Logger**: Change `packages/webcompy/src/webcompy/hydration/_report.py` from `logging.getLogger("webcompy.hydration").warning(...)` to `webcompy.logging.warn(...)` so single summary warnings emit cleanly to `window.console.warn` without hitting PyScript stderr `.py-error`.
  - **Static `ThemeToggle` cookie mismatch**: Keep `ThemeToggle` initial hydration DOM aligned with statically pre-rendered `Theme.SYSTEM` HTML (deferring reactive toggle label synchronization or applying persisted theme cookie post-initial-hydration / alongside a tiny pre-paint inline style resolver) so initial hydration sees zero mismatches on reload while visual theme and toggle state sync seamlessly.
  - **Static `404.html` catch-all mismatch**: Align `docs_app/pages/not_found.py` so static `404.html` does not render path-dependent text/attributes that disagree with arbitrary missed browser URLs during initial hydration.
  - **`BrowserHistoryPort` `JsProxy`**: Add a safe helper `_js_state_to_dict(hist_state)` using `self._browser.pyscript.ffi.is_none(hist_state)` and `hist_state.to_py()` (when `hasattr(hist_state, "to_py")`), returning `result if isinstance(result, dict) else None`. Apply in both `_on_popstate` and `refresh_from_window`.

## Risks / Trade-offs

- [CSS layer specificity interaction with `docs_app` custom styles] → Keep base form-control defaults in `@layer reset` so `@layer components`, `@layer prose`, `@layer webcompy-scope`, and unlayered app stylesheets always win cleanly.
- [Deferring `ThemeToggle` label update until post-hydration vs. SSR dynamic theme CSS] → Applying theme CSS early avoids FOUC for background surfaces while keeping hydrated VDOM of `ThemeToggle` aligned with static HTML, yielding zero mismatches on reload.
- [Browser `to_py()` returning `dict` vs non-plain JS objects in `history.state`] → Type-guard `isinstance(converted, dict)` and fall back to `None` with a console warning instead of crashing navigation.
