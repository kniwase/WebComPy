# Tasks: feat-ui-disclosure-feedback-components

## 0. Artifact alignment (post-rebase baseline)

- [x] 0.1 Update delta spec, design, and tasks to the rebased baseline: roving tabindex, per-instance hydration-stable DOM ids requirement, Collapse content data-state wording, Alert dismiss wording, D3 integration constraints, D10–D12 decisions, DocsCard fact correction
- [x] 0.2 Re-revise artifacts for the redesign: Tabs keep all panels mounted with inactive panels hidden (state-preserving instant switching), Transition-driven panel-switch animation removed from spec/proposal/design/tasks (same-tag patch contract makes it undeliverable), Risks/Non-goals updated

## 1. Tabs

- [x] 1.0 Extract shared private id helper `component_dom_id(kind, context)` into `webcompy/ui/headless/_dom_id.py`; `_overlay_utils.overlay_dom_id` delegates to it (overlay output ids unchanged; existing overlay/primitives unit tests stay green)
- [x] 1.1 Implement headless Tabs: `role="tablist"`/`tab`/`tabpanel` wiring (`aria-selected`, `aria-controls`), reactive active state prop + change callback (uncontrolled default per design D10), all panels mounted with inactive panels hidden via the reactive boolean `hidden` attribute (state-preserving switching, no Transition in Tabs), `data-state="active" | "inactive"` on tab and panel elements, hydration-stable ids per design D12, class pass-through (tablist/tab/panel parts)
- [x] 1.2 Implement tab keyboard model: Left/Right arrows with wrapping + automatic activation, Home/End jump, roving tabindex (`tabindex="0"` active, `"-1"` inactive)
- [x] 1.3 Verify SSR/hydration behavior of hidden panels: inactive panels present in server-rendered output (hidden), `aria-controls` references resolve in-DOM at all times
- [x] 1.4 Implement themed Tabs: token-based tablist/tab/panel rules in `primitives.css` (no animation classes; document the data-state hook for user-side effects)

## 2. Collapse / Accordion

- [x] 2.1 Implement headless Collapse: trigger (`aria-expanded`, `aria-controls`, `data-state="open" | "closed"`, uncontrolled default per D10), content region animated through the Transition element (content carries `data-state="open"` while mounted, removed when closed), hydration-stable ids, class pass-through (trigger/content parts)
- [x] 2.2 Implement themed Collapse with the grid-template-rows natural-height technique (inner overflow-hidden wrapper, enter/leave rules ordered after the steady rule) and document the technique for headless users; disable-animation prop supported
- [x] 2.3 Implement Accordion composing Collapse items with key-based identity and open policy (multi-open default, single-open prop closing siblings), items via `items` prop per design D11, shared open state owned by the Accordion driving controlled Collapse instances

## 3. Feedback components

- [x] 3.1 Implement headless Alert: variant prop with role mapping (error/warning → `role="alert"`, info/success → `role="status"`), optional dismiss action with accessible button (dismiss hides the root via the boolean `hidden` attribute and calls the dismiss callback), class pass-through
- [x] 3.2 Implement headless Progress: `role="progressbar"` with accessible label, determinate (`aria-valuenow/min/max` from props) and indeterminate (omit valuenow, `data-state="indeterminate"`) modes, reactive fill-width style binding, class pass-through
- [x] 3.3 Implement headless Badge (variant attribute, class pass-through), Skeleton (`aria-hidden="true"` placeholders with rectangle/line/circle shape props), and Card (header/body/footer regions via slots, class pass-through)
- [x] 3.4 Implement themed Alert/Progress/Badge/Skeleton/Card rules in `primitives.css` consuming tokens (variant colors from semantic tokens, progress track/fill, skeleton shimmer honoring reduced motion); export all themed pairs from `webcompy.ui.headless`, `webcompy.ui.components`, and `webcompy.ui`

## 4. Unit tests (`tests/test_ui_disclosure.py`, browserless via TestRenderer)

- [x] 4.1 Tabs: ARIA wiring (tablist/tab/panel, aria-selected/controls), panel state preservation across switches (inactive panels stay mounted, hidden toggling), keyboard navigation with wrapping and automatic activation, roving tabindex, `data-state` values, distinct hydration-stable ids across two instances
- [x] 4.2 Collapse: trigger ARIA across toggle, `data-state` transitions, animation disable path; Accordion single-open policy closes siblings, multi-open default
- [x] 4.3 Alert role mapping per variant; dismiss hides root and fires callback
- [x] 4.4 Progress determinate ARIA values and indeterminate omission of `aria-valuenow`
- [x] 4.5 Badge/Skeleton/Card: Skeleton `aria-hidden`, Card region rendering, class pass-through on all (user class appended last)

## 5. E2E and docs

- [x] 5.1 E2E tests (Playwright): `/disclosure` page in `e2e/core/my_app`, `e2e/core/test_disclosure.py` registered in the `components` group of `scripts/run-e2e-tests.sh`; Tabs keyboard navigation (wrapping, automatic activation) and panel-state preservation across switches in the browser; Collapse animated expand/collapse; Accordion single-open behavior
- [x] 5.2 docs_app demo page for the family (Tabs/Collapse/Accordion/Alert/Progress/Badge/Skeleton/Card): `documents/disclosure.md` + `pages/document/disclosure.py` showcase, manifest entry appended at the end of the Guides section; replace docs_app's ad-hoc DocsCard with the themed Card primitive preserving its surface; link from docs navigation (automatic via manifest)
- [ ] 5.3 Update knowledge-maintenance docs: AGENTS.md File→Spec Mapping row, Current Specs row, Framework Invariants entry, `.opencode/skills/webcompy-review/SKILL.md` invariant heading; run `python3 scripts/check-doc-spec-refs.py` (if it fails on the not-yet-archived `ui-disclosure` spec, defer these edits to the archive change and report)

## 6. Validation

- [ ] 6.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 6.2 `uv run pyright` passes
- [ ] 6.3 `uv run python -m pytest tests/ --tb=short` passes
- [ ] 6.4 `uv run python -m webcompy generate` succeeds with the new docs page
- [ ] 6.5 E2E groups affected by the change pass via `scripts/run-e2e-tests.sh`: `components`, `bootstrap-static`, `docs-documents`, `docs-home`
- [ ] 6.6 Run the openspec-verify-change workflow and produce the verification report (do not sync or archive)
