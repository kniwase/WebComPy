# Tasks: feat-ui-primitives-foundation

## 1. Package skeleton

- [x] 1.1 Create `packages/webcompy/src/webcompy/ui/headless/` and `packages/webcompy/src/webcompy/ui/components/` packages with `__init__.py` exports; re-export themed components from `webcompy/ui/__init__.py` top level (keep `theme` and `code_block` exports unchanged)
- [x] 1.2 Document the two-layer contract in `webcompy/ui/README.md`: headless behavior-only rules (structural CSS only, `data-state` vocabularies, class pass-through), themed composition rules, and the three import paths

## 2. Headless Spinner

- [x] 2.1 Implement headless `Spinner` (`@define_component`, `SpinnerProps` TypedDict): `role="status"`, accessible label (label prop as visually-hidden text or `aria-label` fallback), `data-state="loading"`, root `class` pass-through with framework class first

## 3. Themed Spinner and stylesheet delivery

- [x] 3.1 Create `_styles/primitives.css` with the themed Spinner rules consuming design tokens (border/spin indicator using `--color-*`), including a `prefers-reduced-motion` rule that pauses animation; import it from `_styles/index.css` within the existing `@layer` ordering
- [x] 3.2 Implement themed `Spinner` composing the headless Spinner with the default themed classes and forwarding class pass-through props

## 4. Unit tests (`tests/test_ui_primitives_foundation.py`, browserless via TestRenderer)

- [ ] 4.1 Headless Spinner: `role="status"`, accessible label rendering (label prop and aria-label fallback), `data-state="loading"`, no visual styling beyond structural CSS
- [ ] 4.2 Class pass-through: user class appended after framework classes on headless and themed variants
- [ ] 4.3 Themed composition: themed Spinner renders the headless behavior with themed default classes; imports resolve per the three-path requirement (`webcompy.ui.headless`, `webcompy.ui.components`, `webcompy.ui` top level yields themed)
- [ ] 4.4 Stylesheet wiring: `primitives.css` is imported by `index.css` and contains the reduced-motion rule

## 5. Docs and dogfooding

- [ ] 5.1 Add a docs_app section describing the two-layer model (headless vs themed, `data-state` styling, class overrides, layer cascade note) with the Spinner as the worked example; link from docs navigation
- [ ] 5.2 Adopt the themed Spinner in docs_app where loading indicators are used (dogfooding validation)

## 6. Validation

- [ ] 6.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 6.2 `uv run pyright` passes
- [ ] 6.3 `uv run python -m pytest tests/ --tb=short` passes
