# Tasks

## 1. Core Expansion Module (`webcompy/elements/_bind.py`)

- [x] 1.1 Create `packages/webcompy/src/webcompy/elements/_bind.py` with `expand_bind_attr(tag_name, attrs, events)`: pops `":bind"` from `attrs`, validates the Signal kind (`Signal` only — reject `Computed`/`ReadonlySignal`/`ReactiveList`/`ReactiveDict`/non-signals with type-naming `WebComPyException`), determines the binding rule from tag + static `type` attr (see design D3 table), validates value-type discipline (D6), checks bound-attr conflicts (D7), sets the bound attr entry (radio: `Computed` equality), and registers the write-back handler into `events` (chaining a pre-existing same-event handler so binding runs first)
- [x] 1.2 Implement the number write-back converter (design D5: int/float by current Signal type, skip empty/unparseable)
- [x] 1.3 Unit tests for `expand_bind_attr` in isolation: each element-type rule, all error cases (wrong kind, wrong type, conflict, dynamic type, unsupported tag incl. `select`, radio without static `value`), handler chaining order, `:bind` key removed from attrs

## 2. Element Integration

- [x] 2.1 In `packages/webcompy/src/webcompy/elements/types/_element.py` `Element.__init__`, call `expand_bind_attr(self._tag_name, attrs, events)` before storing `self._attrs`/`self._event_handlers` (design D1; `create_element` in `generators.py:43` already routes `:bind` into `attrs`, no change needed there)
- [x] 2.2 Unit tests via element API: `html.INPUT({":bind": sig})` renders `value`, Signal→DOM updates work, DOM→Signal write-back works with fake ports (see `tests/test_unified_render_path.py` patterns), radio group `checked` Computeds sync, no `:bind` attribute on the DOM node, SSR (`ServerDOMPort`) renders bound attr without events

## 3. Template Integration

- [x] 3.1 In `packages/webcompy/src/webcompy/template/_binder.py` `classify_attrs`, accept `:bind` alongside `:ref`: reject `{{ }}` holes inside, `resolve_var` + validate `Signal` (type-naming error), return it so `bind_element` passes `resolved_attrs[":bind"] = signal` into `Element(...)`; update the "only ':ref' is allowed" error message to mention `:bind`
- [x] 3.2 Unit tests: `<input :bind="text">` produces a bound element equivalent to the element API; non-Signal `:bind` error names variable and observed type; `{{ }}` inside `:bind` rejected; other `:`-attrs still rejected with updated message (extend `tests/test_template_binder.py`)

## 4. Spec, Mapping, and Housekeeping

- [ ] 4.1 Apply the delta to `openspec/specs/elements/spec.md` and `openspec/specs/template-engine/spec.md` (via archive/sync flow after implementation)
- [ ] 4.2 Update `AGENTS.md` File→Spec Mapping if a new row is needed for `webcompy/elements/_bind.py` (map to `elements/spec.md`); check `.opencode/skills/webcompy-review/SKILL.md` invariants for stale statements about colon attributes or event handling

## 5. E2E and Verification

- [ ] 5.1 Add e2e page(s) under `e2e/core/my_app/pages/` (e.g., `two_way_binding.py`) exercising: text input round-trip (type → signal → rendered text), number conversion, checkbox toggle, radio group switching, SSR prerender of bound attrs; add Playwright tests under `e2e/core/`
- [ ] 5.2 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short`
- [ ] 5.3 Run the relevant e2e group via `scripts/run-e2e-tests.sh` and `uv run python -m webcompy generate` on docs_app to confirm no regression
