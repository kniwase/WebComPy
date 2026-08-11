# Tasks: feat-ui-form-controls

## 1. Text controls

- [ ] 1.1 Implement headless Input: native `<input>` with type prop (text/email/password/search/tel/url/number), Field binding via the `:bind` mechanism or raw value/change props (mutually exclusive, error when both), class pass-through, `data-invalid` state hook
- [ ] 1.2 Implement headless Textarea: same binding contract on native `<textarea>` with rows prop
- [ ] 1.3 Implement headless Select: native `<select>` with options prop (value/label pairs), same binding contract, class pass-through

## 2. Choice controls

- [ ] 2.1 Implement headless Checkbox: native checkbox with checked binding (Field bool or raw value/change), label association props, class pass-through
- [ ] 2.2 Implement headless Switch: checkbox base with `role="switch"` and `aria-checked` reflecting state, same binding path
- [ ] 2.3 Implement headless Radio and RadioGroup: `fieldset`/`legend`, generated shared `name` for native arrow-key navigation, group value binding (Field string or raw), item value props, class pass-through

## 3. FormField wrapper

- [ ] 3.1 Implement headless FormField: label association, control slot, error region; stable per-instance ids; when the bound field is touched and invalid set `aria-invalid="true"` on the control and associate the error region via `aria-describedby`, otherwise no association; error text gated on touched+invalid
- [ ] 3.2 Wire `data-invalid` propagation from the bound field state to the slotted control

## 4. Themed layer

- [ ] 4.1 Implement themed Input/Textarea/Select composing the headless controls with token-based rules (borders, focus-visible rings, disabled states, invalid states using semantic tokens) in `primitives.css`
- [ ] 4.2 Implement themed Checkbox/Switch/RadioGroup (including switch track/thumb visuals and radio indicator) and themed FormField (label typography, error message styling with danger token)

## 5. Unit tests (`tests/test_ui_form_controls.py`, browserless via TestRenderer)

- [ ] 5.1 Binding contract: Field-bound input syncs value and sets dirty/touched per forms rules; raw value mode invokes change callback; both-modes error case
- [ ] 5.2 Select options rendering and selection binding; Checkbox checked binding; Switch `role="switch"`/`aria-checked`
- [ ] 5.3 RadioGroup: fieldset/legend structure, shared name generation, group value binding updates
- [ ] 5.4 FormField: label association, error gating (no flash when untouched; errors + `aria-invalid` + `aria-describedby` after blur), id stability across re-renders
- [ ] 5.5 `data-invalid` hook follows touched+invalid gating on all bound controls

## 6. E2E and docs

- [ ] 6.1 E2E tests (Playwright): a complete form — typed input triggers validation on blur, error display with ARIA wiring verified in the browser, submit gating via Form, reset restores initial state
- [ ] 6.2 docs_app demo page: full form example (Input/Textarea/Select/Checkbox/Switch/RadioGroup inside FormFields with validators, submit/reset) built from the primitives; link from docs navigation

## 7. Validation

- [ ] 7.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 7.2 `uv run pyright` passes
- [ ] 7.3 `uv run python -m pytest tests/ --tb=short` passes
