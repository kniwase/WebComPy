# Proposal

## Why

During the production browser audit across light and dark modes, isolated demo iframes rendered by `docs_app/static/_demos/standard.html` failed to follow the parent page's active theme and exhibited pervasive contrast, clipping, and scoped-CSS boundary defects (including an invisible `0×0px` `HeadlessSpinner`, white-on-light backgrounds in `fetch_sample`, `transition`, and `teleport`, unreadable inputs in `storage_sync`, unstyled child routes and slotted elements in `routing` and `migration_users`, broken `.task-list` styling in `todo_tutorial`, and clipped fixed-height `400px` iframes).

## What Changes

- **Demo iframe runtime theme & token sync (`demo-iframe-isolation`)**: Load `/_webcompy-ui/index.css` inside `docs_app/static/_demos/standard.html`, mirror the parent document's active `<style data-webcompy-dynamic>` theme rules on initial load and via `MutationObserver` on live theme toggles (with `webcompy-theme` cookie fallback), and theme `#webcompy-loading` using the active tokens.
- **Responsive iframe sizing (`demo-iframe-isolation`, `docs-site-documents`)**: Allow `DemoDisplay` iframes to grow cleanly (or auto-size via measured content height / higher responsive min-height) so taller interactive demos (`forms`, `http-fetch`, `matplotlib_sample`, `i18n-playground`, `migration_users`) are not clipped inside a fixed `400px` box.
- **Tokenization & `webcompy-cid` boundary fixes across demo apps (`demo-iframe-isolation`, `docs-site-documents`, `docs-migration-guide`)**:
  - Replace hardcoded light backgrounds and low-contrast hex colors with theme-aware `var(--color-*)` tokens and WCAG 2.1 AA pairings in `fetch_sample`, `transition`, `storage_sync`, `todo`, `teleport`, `matplotlib_sample`, `ui_form_controls`, `rpc_middleware_mock`, `fetch_middleware_mock`, and `todo_tutorial/step1..step6`.
  - Fix `scoped_style` `webcompy-cid` isolation bugs where parent styles failed to reach slotted or child-component nodes (`migration_users` slotted cards/lists, `routing` nested `RouterView` children and initial `"/"` path display, `todo_tutorial/step3..step6` `.task-list > ul` child styling, and visible dimensions for the `HeadlessSpinner` demo on `ui-primitives`).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `demo-iframe-isolation`: Require `standard.html` demo iframes to load framework design tokens, synchronize live theme changes with the parent document, maintain WCAG AA contrast in both light and dark modes, style across child/slotted component boundaries correctly, and avoid vertical clipping in `DemoDisplay`.
- `docs-site-documents`: Update Examples and Guides tutorial requirements so embedded live demos and inline interactive component demos (`ui-primitives`) follow active theme tokens, preserve child/slotted styling, and avoid clipping.
- `docs-migration-guide`: Ensure the live before/after `migration_users` comparison demo styles slotted/child rows properly, adapts to light/dark themes, and displays without iframe height clipping.

## Known Issues Addressed

- **Demo iframe theme desynchronization**: `standard.html` previously ignored `ThemeManager` CSS injected in the parent document, leaving demos stuck in unstyled browser defaults or mismatched OS polarity when toggling themes.
- **Per-demo contrast & `webcompy-cid` style leaks**: Fixes low-contrast demo surfaces (`1.02:1`–`3.94:1` in dark and OS-inverted modes), invisible `0×0px` `HeadlessSpinner`, unstyled nested `RouterView` views in `routing`, unstyled slotted HTML in `migration_users`, and unstyled child `<ul>` in `todo_tutorial/step3..step6`.
- **Fixed `400px` iframe clipping**: Prevents `forms` (`902px`), `http-fetch` (`718px`), `matplotlib` (`646px`), `i18n-playground` (`497px`), and `migration_users` (`495px`) from being cut off on first view.

## Non-goals

- Core framework `ThemeManager` / `tokens.css` / `prose.css` / overlay fixes (covered in `fix/theme-contrast-and-prose-overflow`, Phase 1 — which this change builds on top of once merged).
- Docs navigation UX, sidebar/TOC overflow, client-side search, heading anchors, code copy button, `<html lang>`, or SSG payload optimization (covered in `feat/docs-ux-a11y-and-payload`, Phase 3).
- Adding new example pages or removing existing demos.

## Impact

- **Demo shell & components (`docs_app`)**: `docs_app/static/_demos/standard.html`, `docs_app/components/demo_display.py`, `docs_app/pages/document/ui_primitives.py`, and demo apps under `docs_app/static/_demos/{fetch_sample,transition,storage_sync,todo,teleport,matplotlib_sample,ui_form_controls,rpc_middleware_mock,fetch_middleware_mock,migration_users,routing,i18n_playground,todo_tutorial/step1..step6}/app.py`.
- **Tests & specs**: Docs E2E checks (`docs-demos`, `docs-matplotlib`, `docs-fetch`) extended to verify iframe theme sync, contrast/visibility (`HeadlessSpinner`, `migration_users`, `routing`), and sizing across light and dark modes, plus `SPEC_INDEX.md` / `webcompy-review/SKILL.md` sync at archive time.
