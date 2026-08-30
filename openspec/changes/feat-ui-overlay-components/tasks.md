# Tasks: feat-ui-overlay-components

## 1. Shared overlay utilities

- [x] 1.1 Implement the focus-trap helper: focusable-element query at trap time, Tab/Shift+Tab boundary cycling, initial focus-in (first focusable or panel with `tabindex="-1"`), and focus capture/return (capture `document.activeElement` on open, restore on close if still present)
- [x] 1.2 Implement document-level listener lifecycle helper: tracked registration/removal for keydown (Escape) and click/pointer (outside-click with exclusion predicate), guaranteeing no listener outlives its owner; unit-test registration/removal symmetry

## 2. Modal

- [x] 2.1 Implement headless Modal: `role="dialog"`, `aria-modal`, labelled-by/aria-label props, reactive `open` prop + `on_close` callback, Escape dismissal, optional backdrop-click dismissal (disable-able), Teleport(body)+Transition composition, `data-state="open"`, class pass-through (root, backdrop, panel parts)
- [x] 2.2 Wire the focus trap into Modal open/close lifecycle (focus-in on open, return on close), including the no-focusable-content case
- [x] 2.3 Implement themed Modal: default classes + `primitives.css` rules (backdrop, panel, token-based styling, default `webcompy-modal` transition classes for open/close)

## 3. Drawer

- [x] 3.1 Implement headless Drawer reusing the Modal accessibility contract: edge prop (left/right/top/bottom) reflected via attribute for styling, focus trap, Escape, Teleport+Transition, `data-state`, class pass-through
- [x] 3.2 Implement themed Drawer: edge-positioned panel rules + default `webcompy-drawer` transition classes per edge

## 4. Dropdown

- [x] 4.1 Implement headless Dropdown trigger/menu: trigger button with `aria-expanded`/`aria-haspopup="menu"`/`aria-controls`, menu with `role="menu"`/`menuitem`, toggle on activation, Teleport+Transition rendering, `data-state` on trigger and menu, class pass-through
- [x] 4.2 Implement menu keyboard model: ArrowDown/ArrowUp with wrapping, Home/End, Escape (close + focus return to trigger), Enter/Space activate focused item and close
- [x] 4.3 Implement outside-click close with trigger exclusion (no toggle race); listener registered on open, removed on close/unmount
- [x] 4.4 Implement themed Dropdown: trigger/menu token-based rules + default `webcompy-dropdown` transition classes

## 5. Toast

- [x] 5.1 Implement `use_toast()` composable: queue state, push function (message, variant, duration), per-toast auto-dismiss timers with default/override/disable, timer cancellation on dismiss and component destroy
- [x] 5.2 Implement headless Toast host + items: Teleport'd container as ARIA live region (`aria-live="polite"`, alert semantics for error variants), manual dismiss action, `data-state="visible"`, leave handling before removal, class pass-through
- [x] 5.3 Implement themed Toast host/items: variant styling (info/success/warning/error) consuming tokens, dismiss button, enter/leave transition classes

## 6. Unit tests (`tests/test_ui_overlay.py`, browserless via TestRenderer + fake ports)

- [x] 6.1 Modal: dialog semantics (role/aria attributes), focus trap cycling incl. no-focusable case, focus return on close, Escape invokes `on_close`, backdrop dismissal and its disable switch, listener cleanup after close/unmount
- [x] 6.2 Drawer: edge prop reflection, shared a11y contract behaviors (trap/Escape/focus return)
- [x] 6.3 Dropdown: trigger ARIA state across toggle, keyboard navigation (arrows wrap, Home/End, Escape returns focus, Enter activates+closes via `click()` dispatch), outside-click close with trigger exclusion, listener cleanup
- [x] 6.4 Toast: push renders into live region, variant semantics, auto-dismiss timing via FakeTransitionPort (advance_time), manual dismiss cancels timers, destroy cancels pending timers (verified via use_toast cleanup)
- [x] 6.5 Integration: overlay content renders under fake `body` via Teleport; closed overlays contribute no content; `data-state` values per vocabulary
- [x] 6.6 Verify focusable-element refinement (`AUDIO`/`VIDEO` require `controls`) and `destroyed` guard for initial-open macro-task race

## 7. E2E and docs

- [x] 7.1 E2E tests (Playwright): Modal open/close with real focus trap verification (Tab cycling in browser), Escape/backdrop close, focus return; Dropdown keyboard navigation and outside click; Toast push/auto-dismiss
- [x] 7.2 docs_app demo pages for Modal, Drawer, Dropdown, Toast; rework the docs_app navbar dropdown onto the Dropdown component (replacing the hand-rolled positioning workaround); link from docs navigation

## 8. Validation

- [x] 8.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [x] 8.2 `uv run pyright` passes
- [x] 8.3 `uv run python -m pytest tests/ --tb=short` passes

## 9. Regression fixes from post-change verification

- [x] 9.1 Reopen the change: revert the spec sync and archive commits so this change can absorb the verification findings
- [x] 9.2 D11: stop event propagation in the headless Dropdown trigger click handler (guarded for fake events)
- [x] 9.3 D12: expose the per-instance transfer id on the component context and derive Dropdown trigger/menu and Modal/Drawer panel/backdrop DOM ids from it (sanitized)
- [x] 9.4 D13: fix docs_app navbar — scoped styles cover the `<button>` trigger with a button reset, menu items carry `role="menuitem"`, desktop menu re-anchored (fixed, below navbar, right-aligned), mobile menu a fixed full-width strip below the navbar (drop `--nav-dropdown-*` dependency)
- [ ] 9.5 Unit tests: trigger click does not reach a document-level listener; two Dropdown instances produce distinct trigger/menu ids and correct `aria-controls` pairing; Modal/Drawer instance ids differ across instances
- [ ] 9.6 E2E: multi-instance Dropdown page — both dropdowns open/close independently, outside click closes, no cross-instance interference; docs navbar dropdown opens and closes on desktop and mobile viewports

## 10. Re-validation

- [ ] 10.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 10.2 `uv run pyright` passes
- [ ] 10.3 `uv run python -m pytest tests/ --tb=short` passes
- [ ] 10.4 `scripts/run-browser-tests.sh` passes (probes hard gate)
- [ ] 10.5 `scripts/run-e2e-tests.sh` full suite passes (all groups, prod + static)
- [ ] 10.6 `openspec validate` passes; visual navbar verification via `webcompy inspect` screenshots

## 11. Spec sync, governance and archive

- [ ] 11.1 Sync delta specs to `openspec/specs/ui-overlay/spec.md`
- [ ] 11.2 Add `ui-overlay` rows to AGENTS.md (File → Spec Mapping, Current Specs) and the review skill invariant list
- [ ] 11.3 `python3 scripts/check-doc-spec-refs.py` passes; re-archive the change and push
