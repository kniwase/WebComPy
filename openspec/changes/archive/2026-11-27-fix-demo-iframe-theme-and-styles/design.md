# Design

## Context

`docs_app` renders interactive Python showcase apps via `docs_app/components/demo_display.py` inside `<iframe src="/_demos/standard.html?app=...">` using a fixed `min-height: 400px` frame, plus inline UI demos on `/documents/basic/ui-primitives`. An audit across all 19 demo iframes in light/dark and OS-inverted themes surfaced three systemic root causes (see `proposal.md`):

1. **Isolated theme CSS**: `standard.html` builds PyScript runtime config dynamically from `window.parent.document`, yet never loads `/_webcompy-ui/index.css` or copies/observes the parent `<style data-webcompy-dynamic>` theme element. Toggling themes in the parent page leaves iframes unstyled or stuck in stale defaults.
2. **Hardcoded colors & `400px` clipping**: Multiple demo `app.py` stylesheets use raw hex values (`#fafafa`, `mistyrose`, `lightcyan`, `#0f172a`, `#2d8fdd`, `#f1f8ff`, unstyled buttons/modals/dropdowns) that fail WCAG 2.1 AA in dark or OS-inverted modes, while taller demos (`forms` `902px`, `http-fetch` `718px`, `matplotlib_sample` `646px`, `i18n-playground` `497px`, `migration_users` `495px`) clip below `min-height: 400px`.
3. **`webcompy-cid` scoped-style boundaries**: Parent component `scoped_style` rules add `[data-webcompy-cid="..."]` attribute selectors that do not match elements created inside child components or passed via slots (`migration_users` slotted list items, `routing` child `RouterView` views, `todo_tutorial/step3..step6` `TodoList` `<ul>`), leaving subtrees unstyled. Meanwhile `HeadlessSpinner` in `ui_primitives.py` ships behavior-only without dimensions CSS (`0×0px`), and `routing` starts with a blank `"Path:"` on `/`.

## Goals / Non-Goals

**Goals:**
- Synchronize `standard.html` initial theme tokens and live parent theme toggles seamlessly without reloading running Pyodide runtimes inside iframes.
- Eliminate iframe vertical clipping on desktop/tablet while preserving responsive containment on narrow screens.
- Bring all 19 demos and the inline `ui-primitives` `HeadlessSpinner` preview to WCAG 2.1 AA contrast and complete visual styling across `webcompy-cid` boundaries in both light and dark modes.

**Non-Goals:**
- Core framework `ThemeManager` / `tokens.css` / `prose.css` modifications (already covered by Phase 1 `fix/theme-contrast-and-prose-overflow`; Phase 2 assumes Phase 1's tokenized `index.css` and `ThemeManager` `color-scheme` rules).
- Navigation chrome, sidebar/TOC scrolling, client-side search, heading links, copy buttons, or SSG bundle optimization (Phase 3).

## Decisions

### 1. Theme Mirroring & Base Tokens inside `standard.html`
- **Decision**: Update `docs_app/static/_demos/standard.html` to:
  1. Inject `<link rel="stylesheet" href="/_webcompy-ui/index.css">` before booting PyScript so every demo has `--color-*`, `--space-*`, `--radius-*`, `--shadow-*`, `reset.css` control defaults, and `components.css` buttons/utilities available automatically, and update `#webcompy-loading` CSS to use `var(--color-bg)` / `var(--color-fg)` / `var(--color-border)` / `var(--color-accent)`.
  2. Synchronize a `<style data-webcompy-dynamic>` element inside `standard.html` `<head>` from `window.parent.document.querySelector('style[data-webcompy-dynamic]')` on load (falling back to reading the `webcompy-theme` cookie or OS `prefers-color-scheme` when `standard.html` has no same-origin parent).
  3. Attach a `MutationObserver` (`characterData: true, childList: true, subtree: true` on parent `<head>` / dynamic style element, cleaned up on `pagehide`/`unload`) so toggling `ThemeToggle` in the parent immediately mirrors the CSS into every live demo iframe without interrupting Pyodide state.
- **Alternatives rejected**: Modifying every individual demo's `app.py` to instantiate its own `ThemeManager` (duplicates cookie watchers across 19 iframes and still leaves `#webcompy-loading` unthemed before Pyodide starts).

### 2. Safe Same-Origin Auto-Sizing for `DemoDisplay`
- **Decision**: Enhance `docs_app/components/demo_display.py` (`DemoDisplay`) and lightweight helper logic (either a small JS hook on iframe `load`/`MutationObserver` inside `DemoDisplay` or `window.postMessage` from `standard.html` `{ type: "webcompy-demo-height", height }` paired with a higher sensible fallback `min-height` per demo metadata when needed) to dynamically match the `<iframe>` height (`clamp(360px, measuredHeight + buffer, 1400px)`) as demo content renders or changes tabs/items.
- **Rationale**: `postMessage` + `ResizeObserver` inside `standard.html` updates frame height asynchronously as PyScript finishes initializing `#webcompy-app` and removes `#webcompy-loading` (so a `400px` skeleton never stays stuck clipping a `902px` form). Keeping a safe fallback `min-height` avoids collapse while booting.
- **Alternatives rejected**: Hardcoding per-page magic pixel heights in Markdown/Python (brittle whenever a demo expands dynamically, e.g. adding rows in `todo` or plotting in `matplotlib`).

### 3. Fixing Scoped CSS (`webcompy-cid`) & Contrast per Demo
- **Decision**:
  - **Component-owned CSS & tokens**: For `routing`, `migration_users`, and `todo_tutorial/step3..step6`, move child-specific rules onto the child components that actually own those DOM nodes (`scoped_style` on child route components and `TodoList`), use `css_text()` un-cid'd demo-app CSS where styling slotted caller markup inside `migration_users`, or pass explicit classes from the parent directly to rendered children. Initialize `routing` demo's displayed current path cleanly (rendering `context.props.path or "/"`).
  - **Token replacement in demos**: Replace raw hardcoded light colors across `fetch_sample`, `transition`, `storage_sync`, `todo`, `teleport`, `matplotlib_sample`, `ui_form_controls`, `rpc_middleware_mock`, `fetch_middleware_mock`, `i18n_playground`, and `todo_tutorial/step1..step6` with framework design tokens (`var(--color-bg-card)`, `var(--color-bg-elevated)`, `var(--color-fg)`, `var(--color-accent)` + `var(--color-on-accent)`, `var(--color-border)`) and `color-mix(in srgb, var(--color-danger) 15%, var(--color-bg-card))` / subtle translucent accents for semantic highlights (e.g., `transition` enter/leave badges).
  - **`ui-primitives` `HeadlessSpinner`**: In `docs_app/pages/document/ui_primitives.py`, supply explicit visual size and tokenized CSS (`width: 1.5rem; height: 1.5rem; border: 2px solid var(--color-border); border-top-color: var(--color-accent); border-radius: 50%; animation: ...`) for the headless spinner preview card while explaining how headless omits built-in chrome by design.

## Risks / Trade-offs

- [Dynamic iframe resizing causing cumulative layout shift below the iframe] → Reserve initial `min-height` matching typical demo height and animate or step height cleanly once `#webcompy-app` mounts.
- [Demo apps loading `/_webcompy-ui/index.css` altering demo layout spacing] → `reset.css` sets `box-sizing: border-box` cleanly; verify every one of the 19 demo iframes visually after wiring `index.css`.
- [`standard.html` `MutationObserver` when parent frame has no `<style data-webcompy-dynamic>` yet] → Re-query parent `<head>` if the dynamic style tag is added later and fall back safely when `window.parent === window`.
