# Tasks: feat-ui-form-controls

## 0. Artifact refresh (post-rebase alignment)

- [x] 0.1 Update proposal/design/specs/tasks for: `:bind` select extension (elements modified), DI-based FormField wiring, `data-state` vocabulary, options-prop RadioGroup, named custom elements, transfer_id-derived hydration-stable ids, docstring/E2E-group validation requirements
- [x] 0.2 `openspec validate feat-ui-form-controls` passes

## 1. `:bind` select extension (`elements`)

- [x] 1.1 Add `_expand_select_bind` to `webcompy/elements/_bind.py`: str-valued Signal requirement (mirror `_expand_text_bind` error), `attrs["value"] = signal`, write-back on `change` (`signal.value = target.value`, dirty first), `blur` marks Field touched, raise on `multiple` attr (single selection only); wire the `select` tag path in `expand_bind_attr` returning `{"value"}` property attrs; update `_SUPPORTED_ELEMENTS` message to include `select`
- [x] 1.2 Extend existing `:bind` unit tests (locate via `grep -rl "expand_bind_attr\|:bind" tests/`): select two-way binding, non-str rejection, explicit `value` conflict rejection, dirty/touched wiring through the Field path

## 2. Headless text controls

- [x] 2.1 Create `webcompy/ui/headless/_form_field_context.py`: frozen dataclass `FormFieldContext` (control_id, error_id, label) and module-private `InjectKey`
- [x] 2.2 Implement headless Input (`headless-input`): native `<input>` via `create_element` with `":bind"` in attrs; `field` xor `value`+`on_change` props (both → error); inject FormFieldContext (default None) to set native `id` and conditional `aria-describedby`; `aria-invalid` computed on touched+invalid; `data-state="valid|invalid"` via Computed; `input_type` static prop (text/email/password/search/tel/url/number); `class_name` pass-through
- [x] 2.3 Implement headless Textarea (`headless-textarea`): same contract on native `<textarea>` with `rows` prop
- [x] 2.4 Implement headless Select (`headless-select`): native `<select>` with `options` prop (value/label TypedDict), same binding contract via the select `:bind` path
- [x] 2.5 Verify the DI provide/inject path with a minimal unit test: a child component rendered inside a parent slot resolves a value provided by the parent context

## 3. Headless choice controls

- [x] 3.1 Implement headless Checkbox (`headless-checkbox`): native checkbox with checked binding (Field bool or raw value/change), optional `label` prop rendered as implicit wrapping label, FormFieldContext consumption, `data-state` hook, class pass-through
- [x] 3.2 Implement headless Switch (`headless-switch`): checkbox base with `role="switch"` and computed `aria-checked`, same binding path
- [x] 3.3 Implement headless Radio (`headless-radio`) and RadioGroup (`headless-radio-group`): Radio is a standalone native radio (caller supplies `name`); RadioGroup renders `fieldset`/`legend` with `options` prop items sharing a `name` generated from the group's transfer id, group value binding (Field string or raw), `data-state` on the fieldset

## 4. Headless FormField

- [ ] 4.1 Implement headless FormField (`headless-form-field`): required `field` prop, `label` (renders `<label for>` when non-empty; omit for group controls), control slot, error region gated on touched+invalid with errors from `field.errors`; generate `control_id`/`error_id` from transfer id (sanitized `#`); `context.provide` the FormFieldContext
- [ ] 4.2 Wire `data-state` on the FormField root following the same touched+invalid gating

## 5. Themed layer

- [ ] 5.1 Implement themed Input/Textarea/Select (`webcompy-input`/`-textarea`/`-select`) composing the headless controls with token-based rules in `primitives.css` (borders, focus-visible ring, disabled, `data-state="invalid"` with danger token)
- [ ] 5.2 Implement themed Checkbox/Switch/RadioGroup (switch track/thumb visuals, radio indicator) and themed FormField (label typography, error text with danger token); forward `class_name` part props to headless so user classes win at equal specificity
- [ ] 5.3 Export: headless names from `webcompy.ui.headless`, themed from `webcompy.ui.components`, themed re-exported at `webcompy.ui`; import-path resolution tests included in unit tier

## 6. Unit tests (`tests/test_ui_form_controls.py`, browserless via TestRenderer; keep free of browser-only APIs for dual-run eligibility)

- [ ] 6.1 Binding contract: Field-bound input syncs value and sets dirty/touched per forms rules; raw value mode invokes change callback; both-modes error case
- [ ] 6.2 Select options rendering and selection binding; Checkbox checked binding; Switch `role="switch"`/`aria-checked`
- [ ] 6.3 RadioGroup: fieldset/legend structure, options expansion, generated shared name distinct across instances, group value binding updates
- [ ] 6.4 FormField: DI wiring end to end (label `for` equals control native id via injected context), error gating (no flash when untouched; errors + `aria-invalid` + `aria-describedby` after blur), id stability across re-renders, standalone control without context
- [ ] 6.5 `data-state="valid|invalid"` follows touched+invalid gating on all bound controls; raw-mode controls report `valid`

## 7. E2E and docs

- [ ] 7.1 docs_app demo page (`docs_app/pages/demo/ui_form_controls.py`, route `/sample/ui-form-controls`): full form (Input/Textarea/Select/Checkbox/Switch/RadioGroup in FormFields with validators, submit gated by Form, reset); link from docs navigation
- [ ] 7.2 E2E test `e2e/core/test_ui_form_controls.py`: typed input triggers validation on blur, error display with `aria-invalid`/`aria-describedby` wiring verified in the browser, submit gating via Form, reset restores initial state; register new `ui-form-controls` group in `scripts/run-e2e-tests.sh` `E2E_GROUPS`
- [ ] 7.3 Docs E2E: add a page test for the demo under `e2e/docs/` (pattern: `test_transition.py`) and register it in the `docs-demos` group

## 8. Validation

- [ ] 8.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 8.2 `uv run pyright` passes
- [ ] 8.3 `python3 scripts/check-docstrings.py` passes (all new public interfaces carry Google-style docstrings; no OpenSpec references in docstrings/comments)
- [ ] 8.4 `uv run python scripts/check-browser-imports.py` passes
- [ ] 8.5 `uv run python -m pytest tests/ --tb=short` passes
- [ ] 8.6 E2E for all affected groups pass: `scripts/run-e2e-tests.sh ui-form-controls`, `docs-demos`, `components`, `interaction`
