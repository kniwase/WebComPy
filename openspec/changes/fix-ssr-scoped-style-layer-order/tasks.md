# Tasks: fix-ssr-scoped-style-layer-order

## 1. Core Implementation

- [x] 1.1 Split `HeadElement.get_head_content_html()` in `packages/webcompy/src/webcompy/elements/_head.py`: keep title, meta, `*[hidden]` utility style, dynamic styles, and app links in `get_head_content_html()`; move per-component `<style data-webcompy-cid>` and `<style data-webcompy-cid-rx>` generation into a new `get_scoped_styles_html()` method
- [x] 1.2 Update `packages/webcompy-server/src/webcompy_server/_html.py` (`_generate_html_impl`): insert `get_head_content_html()` output after `<head>` as today, and insert `get_scoped_styles_html()` output immediately after the `/_webcompy-ui/index.css` link (anchor a `replace` on the rendered link HTML, kept adjacent to the link element definition)

## 2. Unit Tests

- [ ] 2.1 Add a test (e.g., in `tests/test_framework_ui_html.py`) asserting that in generated HTML every `data-webcompy-cid` / `data-webcompy-cid-rx` style element appears after the `/_webcompy-ui/index.css` link, for an app with scoped-style components
- [ ] 2.2 Add a test asserting `get_scoped_styles_html()` returns only scoped style elements and `get_head_content_html()` no longer contains `data-webcompy-cid`
- [ ] 2.3 Run existing scoped-CSS test suites (`tests/test_scoped_css.py`, `tests/test_reactive_scoped_style.py`, `tests/test_reactive_app_style.py`, `tests/test_scoped_style_layer.py` if present) and confirm no regressions; update any test that asserts scoped styles appear before stylesheet links

## 3. Spec Updates

- [ ] 3.1 Sync delta specs to main specs: apply MODIFIED requirements (reset scenario wording, components.css repositioning) and the ADDED SSR emission-order requirement to `openspec/specs/css-architecture/spec.md`; apply the head-content API split to `openspec/specs/head-vdom/spec.md`
- [ ] 3.2 Update the AGENTS.md File → Spec Mapping / invariant notes if the spec reference structure changed, and run `python3 scripts/check-doc-spec-refs.py`

## 4. Verification

- [ ] 4.1 Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright`
- [ ] 4.2 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 4.3 Run `uv run python -m webcompy generate` on docs_app and inspect a generated page's `<head>` ordering (scoped styles after index.css link)
- [ ] 4.4 Run docs E2E group (`scripts/run-e2e-tests.sh <docs-group>`) and confirm scoped styles apply as authored (e.g., `.docs-pager a` computed color matches `var(--color-fg)`); check prod and static modes
