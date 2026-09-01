# Tasks: feat-docs-api-reference

## 1. Tooling

- [ ] 1.1 Extract the public-API surface resolver from `scripts/check-docstrings.py` into `scripts/_api_surface.py`; update the checker to import it; confirm checker behavior unchanged (baseline tests green)
- [ ] 1.2 Write `scripts/generate_api_reference.py` (skeleton emission with author regions) + `--check` mode; unit-test both modes against a fixture module
- [ ] 1.3 Wire `--check` into CI (openspec/lint job) and `scripts/run-local-ci` docs; document regeneration usage in the webcompy-docs-development skill

## 2. Reference pages (one task per page group; author prose as you go)

- [ ] 2.1 `api_core_app_components.md` (app/config + components incl. lifecycle/context APIs)
- [ ] 2.2 `api_core_template_markdown.md` (template, render_template/render_markdown, css helpers, markdown-document types)
- [ ] 2.3 `api_core_reactivity.md` (signal + effect + readonly + composables)
- [ ] 2.4 `api_core_elements_routing.md` (elements, boundaries, router, di)
- [ ] 2.5 `api_core_data.md` (ajax, aio, forms, storage, events, resources)
- [ ] 2.6 `api_ui.md` (theme, code block, headless/themed components, styles)
- [ ] 2.7 `api_server_cli.md` (webcompy_server incl. rpc/contrib/ports, webcompy_cli configs, webcompy.rpc client surface)
- [ ] 2.8 `api_testing.md` (webcompy_testing)

## 3. Wiring and coverage

- [ ] 3.1 Register `API Reference` category (last); coverage test: every resolved public symbol appears exactly once across pages
- [ ] 3.2 Basic/Advanced pages: append "Full API" links to symbol tables; link-check passes

## 4. Verification

- [ ] 4.1 `python3 scripts/check-docstrings.py` (strict still green) + `generate_api_reference.py --check` green
- [ ] 4.2 `ruff`/`pyright`/unit + `webcompy generate` + docs E2E for new pages (prod + static) + `check-doc-spec-refs.py` + `openspec validate feat-docs-api-reference`
