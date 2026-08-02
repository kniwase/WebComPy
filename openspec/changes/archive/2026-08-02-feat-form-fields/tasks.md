# Tasks

## 1. Field and Validators (`webcompy/forms/`)

- [x] 1.1 Create `packages/webcompy/src/webcompy/forms/_validators.py`: `Validator` type alias and the seven factories (`required`, `min_length`, `max_length`, `pattern`, `email`, `min_value`, `max_value`) per design D3
- [x] 1.2 Create `packages/webcompy/src/webcompy/forms/_field.py`: `Field` class and `use_field` per design D2 (value/errors/valid/invalid/touched/dirty/reset; touched/dirty as plain non-transferred Signals)
- [x] 1.3 Create `packages/webcompy/src/webcompy/forms/__init__.py` exporting the public API; unit tests for Field reactivity, reset, and every validator (incl. custom messages, `required(False)`, multi-validator accumulation)

## 2. `:bind` + Field Integration

- [x] 2.1 Extend `packages/webcompy/src/webcompy/elements/_bind.py` `expand_bind_attr` with a `Field` branch (design D4): bind `field.value`, dirty-on-write-back, blur→touched chaining
- [x] 2.2 Unit tests: Field accepted on all supported element types; dirty/touched wiring; type discipline applies to `field.value`; user `@blur` chained after touched

## 3. Form Aggregation

- [x] 3.1 Create `packages/webcompy/src/webcompy/forms/_form.py`: `Form` class and `use_form` per design D5 (aggregate Computeds, touch_all, reset, values, submit with preventDefault/validity gate/async/submitting/submit_error via `AsyncWrapper`)
- [x] 3.2 Unit tests: aggregate valid/touched/dirty; submit blocked when invalid (touch_all observable); successful sync/async submit; exception captured into `submit_error`; `preventDefault` called (fake DOM event from `tests/conftest.py`)

## 4. Spec, Mapping, and Housekeeping

- [x] 4.1 Apply the delta: create `openspec/specs/forms/spec.md`, apply ADDED requirement to `openspec/specs/elements/spec.md` (archive/sync flow)
- [x] 4.2 Update `AGENTS.md` File→Spec Mapping (`webcompy/forms/` → `forms/spec.md`) and the Current Specs list; update `.opencode/skills/webcompy-review/SKILL.md` spec list accordingly

## 5. E2E and Verification

- [x] 5.1 Add e2e page `e2e/core/my_app/pages/form_fields.py` + Playwright test: full login-form scenario (validation messages gated on touched, dirty tracking, submit blocked while invalid, successful submit updates UI)
- [x] 5.2 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short`
- [x] 5.3 Run relevant e2e group via `scripts/run-e2e-tests.sh` and `uv run python -m webcompy generate` on docs_app
