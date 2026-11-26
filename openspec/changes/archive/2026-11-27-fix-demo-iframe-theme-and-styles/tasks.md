# Tasks

## 1. IFrame Shell Theme & Size Synchronization

- [x] 1.1 Update `docs_app/static/_demos/standard.html` to link `/_webcompy-ui/index.css`, theme `#webcompy-loading` with tokens, clone parent `<style data-webcompy-dynamic>` rules on startup, and mirror live theme changes via `MutationObserver` (plus `webcompy-theme` cookie fallback when standalone); verify live toggling in Playwright across light/dark/system modes.
- [x] 1.2 Add `ResizeObserver` height reporting in `standard.html` and corresponding iframe height adaptation in `docs_app/components/demo_display.py`; verify tall demos (`forms`, `http-fetch`, `matplotlib`, `i18n-playground`, `from-jinja2-fastapi` migration demo) render without clipping below `400px`.

## 2. Scoped Styling Boundaries & Inline Preview Fixes

- [x] 2.1 Fix `webcompy-cid` boundary styling in `docs_app/static/_demos/migration_users/app.py` (style slotted elements via component-owned/un-scoped demo CSS and tokenize light/dark cards/inputs) and `docs_app/static/_demos/routing/app.py` (style child route views cleanly and ensure initial route displays `"/"` instead of blank text); verify rendered child styles in browser inspection.
- [x] 2.2 Fix `.task-list` styling across `docs_app/static/_demos/todo_tutorial/step3/app.py` through `step6/app.py` so `TodoList` child `<ul>`/item rows inherit list styles cleanly, and replace hardcoded button/surface colors with design tokens; verify all 6 tutorial steps in light and dark mode.
- [x] 2.3 Give `HeadlessSpinner` visible dimensions and tokenized border/accent contrast in `docs_app/pages/document/ui_primitives.py`; verify bounding box `> 0px` in Playwright.

## 3. Demo Color Contrast & Tokenization

- [x] 3.1 Tokenize surfaces, text, buttons, inputs, modals, and semantic highlights (replacing raw hexes/named light colors like `#fafafa`, `mistyrose`, `lightcyan`, `#0f172a`, `#2d8fdd`, `#f1f8ff`) across `fetch_sample`, `transition`, `storage_sync`, `todo`, `teleport`, `matplotlib_sample`, `ui_form_controls`, `rpc_middleware_mock`, `fetch_middleware_mock`, `i18n_playground`, and `hello_world` under `docs_app/static/_demos/`; verify WCAG 2.1 AA contrast (`>= 4.5:1`) in both light and dark modes across all 19 demos.

## 4. Verification & Spec Sync

- [x] 4.1 Extend docs E2E / browser audit tests (`e2e/` and `tests/`) to assert parent-to-iframe theme synchronization, visible `HeadlessSpinner`, styled child/slotted demo nodes, unclipped iframe heights, and zero console errors in both `prod` and `static` modes; run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/`, `uv run python -m webcompy generate`, and `scripts/run-e2e-tests.sh`.
- [x] 4.2 Before archiving, sync delta specs into `openspec/specs/` and update `openspec/SPEC_INDEX.md` and `.agents/skills/webcompy-review/SKILL.md` (`python3 scripts/check-doc-spec-refs.py`).
