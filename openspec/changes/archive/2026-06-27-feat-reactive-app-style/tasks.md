# Tasks: Reactive App-Level Style

## 1. Framework core

- [x] 1.1 Add `webcompy/app/styles.py` with `reactive_style(selector, vars_dict)` and `reactive_block(selector, content)` helpers returning `Computed[str]`
- [x] 1.2 Re-export `reactive_style` and `reactive_block` from `webcompy/app/__init__.py`
- [x] 1.3 Add `WebComPyApp.append_style(content: str | Computed[str])` method (deferred-ops aware, like `append_link`)
- [x] 1.4 Add `RenderContext.append_style(content)` method delegating to root
- [x] 1.5 Add `AppDocumentRoot.append_style(content)` method delegating to head

## 2. Head element integration

- [x] 2.1 Add `_styles: list[str | Computed[str]] = []` and `_style_callbacks: dict[int, CallbackConsumerNode] = {}` to `HeadElement.__init__`
- [x] 2.2 Add `HeadElement.append_style(content)` method that appends to `_styles` and (in pyscript) wires `Computed.on_after_updating(callback)` if content is a `Computed`
- [x] 2.3 Extend `HeadElement._render()` (pyscript) to emit one `<style data-webcompy-dynamic="{id}">` per registered style if not already present; wrap content in `@layer webcompy-dynamic { ... }`
- [x] 2.4 Extend `HeadElement.get_head_content_html()` (SSR) to emit the same elements with the current `Computed` value
- [x] 2.5 Ensure subscription cleanup via the existing `HeadElement._cleanup_consumers` mechanism

## 3. CSS cascade update

- [x] 3.1 Update `webcompy/ui/_styles/index.css` to include `webcompy-dynamic` in the layer declaration: `@layer reset, tokens, components, webcompy-scope, webcompy-dynamic;`

## 4. Tests

- [x] 4.1 Add `tests/test_reactive_app_style.py` with:
  - [x] 4.1.1 Unit test: `reactive_style(":root", {"--x": "red"})` produces `":root {\n  --x: red;\n}"`
  - [x] 4.1.2 Unit test: `reactive_style` with a `Signal[str]` re-evaluates when the signal changes
  - [x] 4.1.3 Unit test: `reactive_style` with a callable in the value dict re-evaluates when the callable is called
  - [x] 4.1.4 Unit test: `reactive_block` wraps a single content string in a selector
  - [x] 4.1.5 Unit test: `app.append_style(static_str)` renders the static string
  - [x] 4.1.6 Unit test: `app.append_style(computed_str)` renders the computed value at SSR time
  - [x] 4.1.7 Unit test: multiple `append_style` calls create separate `<style data-webcompy-dynamic>` elements
  - [x] 4.1.8 VDOM test: subscription updates the DOM element's `textContent` when the computed changes
  - [x] 4.1.9 VDOM test: subscription is disposed when the head element is cleaned up
  - [x] 4.1.10 Test: rendered style is wrapped in `@layer webcompy-dynamic { ... }`

## 5. Documentation

- [x] 5.1 Add a section to `webcompy/app/README.md` (or equivalent) explaining `append_style` and `reactive_style` with a runnable example
- [x] 5.2 Update `AGENTS.md` Current Specs and file→spec mapping (add `app-styles`)

## 6. Verification

- [x] 6.1 `uv run ruff check .` — clean
- [x] 6.2 `uv run pyright` — 0 errors
- [x] 6.3 `uv run python -m pytest tests/ --tb=short` — all pass
- [x] 6.4 `uv run python -m webcompy generate --app docs_app.bootstrap:app` — succeeds
- [x] 6.5 `scripts/run-e2e-tests.sh` — passes (focus on `docs-home` for any visual regression)

## 7. OpenSpec archive

- [ ] 7.1 Archive this change via `openspec archive feat-reactive-app-style` (after PR merge) — deferred per design
- [ ] 7.2 Verify `openspec/specs/app-styles/spec.md` and the deltas to `app` and `css-architecture` are correctly synced — deferred per design
