# Tasks: Reactive Scoped Style

## 1. Framework core

- [x] 1.1 Add `webcompy/components/_reactive_scoped_style.py` with `ReactiveScopedStyle` class and `reactive_scoped_style()` function
- [x] 1.2 Add `_reactive_styles: list[ReactiveScopedStyle] = []` attribute to `ComponentGenerator.__init__`
- [x] 1.3 Add `use_reactive_scoped_style(style: ReactiveScopedStyle)` method to `ComponentContext` that appends to the active generator's `_reactive_styles`
- [x] 1.4 Detect calls outside an active component context and raise a clear `WebComPyException` (decision 5 risk mitigation)
- [x] 1.5 Re-export `reactive_scoped_style` and `ReactiveScopedStyle` from `webcompy/components/__init__.py`
- [x] 1.6 Update `AGENTS.md` Current Specs and file→spec mapping (add `reactive-scoped-style`)

## 2. Head element integration

- [x] 2.1 Extend `HeadElement._render()` to iterate over each generator's `_reactive_styles` and emit `<style data-webcompy-cid-rx="{cid}-{index}">` elements in the browser
- [x] 2.2 Wire `Computed[str].on_after_updating(callback)` for each reactive style; the callback updates the matching `<style>` element's `textContent`
- [x] 2.3 Confirm subscription cleanup is automatic via the existing `EffectScope` in `Component.__setup()` (Decision 7)
- [x] 2.4 Extend `HeadElement.get_head_content_html()` (the SSR path) to emit one `<style data-webcompy-cid-rx>` per reactive style with the current `Computed` value

## 3. CSS rendering reuse

- [x] 3.1 In `ReactiveScopedStyle.render_css(cid)`, reuse the existing `_scope_combinator_selector` and `_generate_css_recursive` helpers from `webcompy/components/_generator.py` to keep rendering consistent with the static path
- [x] 3.2 Wrap the rendered CSS in `@layer webcompy-scope { ... }` to match the static path
- [x] 3.3 If a future change introduces a different layer for reactive styles, this is the only place to update

## 4. Tests

- [x] 4.1 Add `tests/test_reactive_scoped_style.py` with:
  - [x] 4.1.1 Unit test: `reactive_scoped_style(lambda: {...}).get_computed_dict().value` returns the dict
  - [x] 4.1.2 Unit test: `render_css(cid)` produces the same output as the static `scoped_style` getter for a non-signal dict
  - [x] 4.1.3 Unit test: when the signal changes, the rendered CSS string changes
  - [x] 4.1.4 Unit test: multiple reactive styles per component render as separate elements
  - [x] 4.1.5 Unit test: static `scoped_style` and reactive style coexist (different element attributes)
  - [x] 4.1.6 Unit test: `use_reactive_scoped_style` outside a component raises a clear error
  - [x] 4.1.7 VDOM unit test: `HeadElement.get_head_content_html()` includes `<style data-webcompy-cid-rx>` with the initial value
  - [x] 4.1.8 VDOM unit test: subscription callback updates the DOM element's `textContent` when the signal changes

## 5. Documentation

- [x] 5.1 Add a section to `webcompy/components/README.md` (or equivalent) explaining reactive scoped styles with a runnable example
- [x] 5.2 Document the design choice (per-component element, two Computeds, distinct attribute) in the design.md file (already done; double-check after implementation)

## 6. Verification

- [x] 6.1 `uv run ruff check .` — clean
- [x] 6.2 `uv run pyright` — 0 errors
- [x] 6.3 `uv run python -m pytest tests/ --tb=short` — all pass
- [x] 6.4 `uv run python -m webcompy generate --app docs_app.bootstrap:app` — succeeds
- [x] 6.5 `scripts/run-e2e-tests.sh` — passes (focus on `docs-home` and any component-level tests)

## 7. OpenSpec archive

- [ ] 7.1 Archive this change via `openspec archive feat-reactive-scoped-style` (after PR merge)
- [ ] 7.2 Verify `openspec/specs/reactive-scoped-style/spec.md` and the modification to `openspec/specs/components/spec.md` are correctly synced
