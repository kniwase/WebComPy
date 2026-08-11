# Tasks: feat-ui-overlay-components

## 1. Shared overlay utilities

- [ ] 1.1 Implement the focus-trap helper: focusable-element query at trap time, Tab/Shift+Tab boundary cycling, initial focus-in (first focusable or panel with `tabindex="-1"`), and focus capture/return (capture `document.activeElement` on open, restore on close if still present)
- [ ] 1.2 Implement document-level listener lifecycle helper: tracked registration/removal for keydown (Escape) and click/pointer (outside-click with exclusion predicate), guaranteeing no listener outlives its owner; unit-test registration/removal symmetry

## 2. Modal

- [ ] 2.1 Implement headless Modal: `role="dialog"`, `aria-modal`, labelled-by/aria-label props, reactive `open` prop + `on_close` callback, Escape dismissal, optional backdrop-click dismissal (disable-able), Teleport(body)+Transition composition, `data-state="open"`, class pass-through (root, backdrop, panel parts)
- [ ] 2.2 Wire the focus trap into Modal open/close lifecycle (focus-in on open, return on close), including the no-focusable-content case
- [ ] 2.3 Implement themed Modal: default classes + `primitives.css` rules (backdrop, panel, token-based styling, default `webcompy-modal` transition classes for open/close)

## 3. Drawer

- [ ] 3.1 Implement headless Drawer reusing the Modal accessibility contract: edge prop (left/right/top/bottom) reflected via attribute for styling, focus trap, Escape, Teleport+Transition, `data-state`, class pass-through
- [ ] 3.2 Implement themed Drawer: edge-positioned panel rules + default `webcompy-drawer` transition classes per edge

## 4. Dropdown

- [ ] 4.1 Implement headless Dropdown trigger/menu: trigger button with `aria-expanded`/`aria-haspopup="menu"`/`aria-controls`, menu with `role="menu"`/`menuitem`, toggle on activation, Teleport+Transition rendering, `data-state` on trigger and menu, class pass-through
- [ ] 4.2 Implement menu keyboard model: ArrowDown/ArrowUp with wrapping, Home/End, Escape (close + focus return to trigger), Enter/Space activate focused item and close
- [ ] 4.3 Implement outside-click close with trigger exclusion (no toggle race); listener registered on open, removed on close/unmount
- [ ] 4.4 Implement themed Dropdown: trigger/menu token-based rules + default `webcompy-dropdown` transition classes

## 5. Toast

- [ ] 5.1 Implement `use_toast()` composable: queue state, push function (message, variant, duration), per-toast auto-dismiss timers with default/override/disable, timer cancellation on dismiss and component destroy
- [ ] 5.2 Implement headless Toast host + items: Teleport'd container as ARIA live region (`aria-live="polite"`, alert semantics for error variants), manual dismiss action, `data-state="visible"`, leave handling before removal, class pass-through
- [ ] 5.3 Implement themed Toast host/items: variant styling (info/success/warning/error) consuming tokens, dismiss button, enter/leave transition classes

## 6. Unit tests (`tests/test_ui_overlay.py`, browserless via TestRenderer + fake ports)

- [ ] 6.1 Modal: dialog semantics (role/aria attributes), focus trap cycling incl. no-focusable case, focus return on close, Escape invokes `on_close`, backdrop dismissal and its disable switch, listener cleanup after close/unmount
- [ ] 6.2 Drawer: edge prop reflection, shared a11y contract behaviors (trap/Escape/focus return)
- [ ] 6.3 Dropdown: trigger ARIA state across toggle, keyboard navigation (arrows wrap, Home/End, Escape returns focus, Enter activates+closes), outside-click close with trigger exclusion, listener cleanup
- [ ] 6.4 Toast: push renders into live region, variant semantics, auto-dismiss timing (fake time), manual dismiss cancels timers, destroy cancels pending timers
- [ ] 6.5 Integration: overlay content renders under fake `body` via Teleport; closed overlays contribute no content; `data-state` values per vocabulary

## 7. E2E and docs

- [ ] 7.1 E2E tests (Playwright): Modal open/close with real focus trap verification (Tab cycling in browser), Escape/backdrop close, focus return; Dropdown keyboard navigation and outside click; Toast push/auto-dismiss
- [ ] 7.2 docs_app demo pages for Modal, Drawer, Dropdown, Toast; rework the docs_app navbar dropdown onto the Dropdown component (replacing the hand-rolled positioning workaround); link from docs navigation

## 8. Validation

- [ ] 8.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 8.2 `uv run pyright` passes
- [ ] 8.3 `uv run python -m pytest tests/ --tb=short` passes
