# Tasks: feat-ui-disclosure-feedback-components

## 1. Tabs

- [ ] 1.1 Implement headless Tabs: `role="tablist"`/`tab`/`tabpanel` wiring (`aria-selected`, `aria-controls`), reactive active state prop + change callback, all panels rendered with inactive panels hidden, `data-state="active" | "inactive"`, class pass-through (tablist/tab/panel parts)
- [ ] 1.2 Implement tab keyboard model: Left/Right arrows with wrapping + automatic activation, Home/End jump
- [ ] 1.3 Implement optional panel-switch animation through the Transition element (default themed class set, disable-able prop)
- [ ] 1.4 Implement themed Tabs: token-based tablist/tab/panel rules + default transition classes in `primitives.css`

## 2. Collapse / Accordion

- [ ] 2.1 Implement headless Collapse: trigger (`aria-expanded`, `aria-controls`), reactive open state + change callback, expand/collapse through the Transition element, `data-state="open" | "closed"`, class pass-through (trigger/content parts)
- [ ] 2.2 Implement themed Collapse with the grid-template-rows natural-height technique (inner overflow-hidden wrapper) and document the technique for headless users; disable-animation prop supported
- [ ] 2.3 Implement Accordion composing Collapse items with key-based identity and open policy (multi-open default, single-open prop closing siblings)

## 3. Feedback components

- [ ] 3.1 Implement headless Alert: variant prop with role mapping (error/warning → `role="alert"`, info/success → `role="status"`), optional dismiss action with accessible button, class pass-through
- [ ] 3.2 Implement headless Progress: `role="progressbar"` with accessible label, determinate (`aria-valuenow/min/max` from props) and indeterminate (omit valuenow, `data-state="indeterminate"`) modes, class pass-through
- [ ] 3.3 Implement headless Badge (variant attribute, class pass-through), Skeleton (`aria-hidden="true"` placeholders with rectangle/line/circle shape props), and Card (header/body/footer regions, class pass-through)
- [ ] 3.4 Implement themed Alert/Progress/Badge/Skeleton/Card rules in `primitives.css` consuming tokens (variant colors from semantic tokens, progress track/fill, skeleton shimmer honoring reduced motion)

## 4. Unit tests (`tests/test_ui_disclosure.py`, browserless via TestRenderer)

- [ ] 4.1 Tabs: ARIA wiring (tablist/tab/panel, aria-selected/controls), panel state preservation across switches (hidden not removed), keyboard navigation with wrapping and automatic activation, `data-state` values
- [ ] 4.2 Collapse: trigger ARIA across toggle, `data-state` transitions, animation disable path; Accordion single-open policy closes siblings, multi-open default
- [ ] 4.3 Alert role mapping per variant; dismiss action wiring
- [ ] 4.4 Progress determinate ARIA values and indeterminate omission of `aria-valuenow`
- [ ] 4.5 Badge/Skeleton/Card: Skeleton `aria-hidden`, Card region rendering, class pass-through on all

## 5. E2E and docs

- [ ] 5.1 E2E tests (Playwright): Tabs keyboard navigation and animated panel switch in the browser; Collapse animated expand/collapse; Accordion single-open behavior
- [ ] 5.2 docs_app demo page for the family (Tabs/Collapse/Accordion/Alert/Progress/Badge/Skeleton/Card); replace docs_app's ad-hoc Card with the primitive; link from docs navigation

## 6. Validation

- [ ] 6.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 6.2 `uv run pyright` passes
- [ ] 6.3 `uv run python -m pytest tests/ --tb=short` passes
