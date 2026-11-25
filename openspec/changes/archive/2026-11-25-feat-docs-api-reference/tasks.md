# Tasks: feat-docs-api-reference

## 1. Tooling

- [x] 1.1 Extract the public-API surface resolver from `scripts/check-docstrings.py` into `scripts/_api_surface.py`; update the checker to import it; confirm checker behavior unchanged (baseline tests green)
- [x] 1.2 Write `scripts/generate_api_reference.py` (skeleton emission with author regions) + `--check` mode; unit-test both modes against a fixture module
- [x] 1.3 Wire `--check` into CI (openspec/lint job) and `scripts/run-local-ci` docs; document regeneration usage in the webcompy-docs-development skill

## 2. Reference pages (one task per page group; author prose as you go)

- [x] 2.1 `api_core_app_components.md` (app/config + components incl. lifecycle/context APIs)
- [x] 2.2 `api_core_template_markdown.md` (template, render_template/render_markdown, css helpers, markdown-document types)
- [x] 2.3 `api_core_reactivity.md` (signal + effect + readonly + composables)
- [x] 2.4 `api_core_elements_routing.md` (elements, boundaries, router, di)
- [x] 2.5 `api_core_data.md` (ajax, aio, forms, storage, events, resources)
- [x] 2.6 `api_ui.md` (theme, code block, headless/themed components, styles)
- [x] 2.7 `api_server_cli.md` (webcompy_server incl. rpc/contrib/ports, webcompy_cli configs, webcompy.rpc client surface)
- [x] 2.8 `api_testing.md` (webcompy_testing)

## 3. Wiring and coverage

- [x] 3.1 Register `API Reference` category (last); coverage test: every resolved public symbol appears exactly once across pages
- [x] 3.2 Basic/Advanced pages: append "Full API" links to symbol tables; link-check passes

## 4. Verification

- [x] 4.1 `python3 scripts/check-docstrings.py` (strict still green) + `generate_api_reference.py --check` green
- [x] 4.2 `ruff`/`pyright`/unit + `webcompy generate` + docs E2E for new pages (prod + static) + `check-doc-spec-refs.py` + `openspec validate feat-docs-api-reference`
