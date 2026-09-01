# Tasks: feat-docs-basic-usage

## 1. Core concept pages

- [ ] 1.1 Write `docs_app/documents/basic_components.md` + wrapper + manifest entry (definition forms and name derivation, props, slots, lifecycle hooks, static scoped styles, `:host` basics, `display` kwarg)
- [ ] 1.2 Write `docs_app/documents/basic_template_html.md` (interpolation incl. reactivity nuance, safe expressions, filters list, `{% if %}`/`{% for %}` + `loop` metadata, `{# #}`/`{% raw %}`, `@click`/`:ref`/`:bind`, component tags; callout listing rejected Jinja2 directives and the component-based replacement)
- [ ] 1.3 Write `docs_app/documents/basic_reactive_state.md` (`Signal`/`Computed`/`ReactiveList`/`ReactiveDict`, `use_state`/`use_computed`/`use_reactive_list`/`use_reactive_dict`, equality contract, effect basics)
- [ ] 1.4 Write `docs_app/documents/basic_elements_events.md` (html namespace, fragments, `repeat`/`switch` helpers, keyed list basics, `DOMEvent`, `DomNodeRef`)
- [ ] 1.5 Write `docs_app/documents/basic_markdown_documents.md` (`render_markdown` options, `load_markdown_document`, frontmatter formats, TOC, `prose.css`, authoring docs pages for your own app)

## 2. App basics pages

- [ ] 2.1 Write `docs_app/documents/basic_routing.md` (flat `RouterPage` table, modes, params/query, `RouterLink` + `active_class`, `use_router`; Next steps → advanced routing)
- [ ] 2.2 Write `docs_app/documents/basic_forms.md` (`use_field`/`use_form`, validators, `:bind`, then UI controls: Input/Textarea/Select/Checkbox/Switch/Radio/RadioGroup/FormField themed usage; Next steps → headless contracts)
- [ ] 2.3 Write `docs_app/documents/basic_http_async.md` (`HttpClient` verbs, `use_async_result` states/predicates, `response_type` typed decode basics; Next steps → transfer opt-out, watch, scheduler)
- [ ] 2.4 Write `docs_app/documents/basic_styling.md` (scoped dict vs `css_text` basics, layer model in one diagram, `use_theme`, app-level link; Next steps → reactive scoped styles, `css_text_template`)
- [ ] 2.5 Write `docs_app/documents/basic_storage.md` (`use_local_storage`, `use_session_storage`; tip box only for `sync_tabs`)
- [ ] 2.6 Write `docs_app/documents/basic_error_handling.md` (`ErrorBoundary`, fallback/reset; Next steps → SSR/SSG policy)

## 3. UI trio revision

- [ ] 3.1 Rework `ui_primitives.md` as the two-layer concept entry (headless contract, themed composition, import paths, stylesheet delivery) and have overlay/disclosure link to it
- [ ] 3.2 Add consistent component tables to `overlay.md` and `disclosure.md` (component, purpose, key props, headless/themed availability)

## 4. Wiring and verification

- [ ] 4.1 Register all 11 pages in `DOCS_SECTIONS` Basic Usage in design order; ensure Advanced pages that will serve as counterparts have back-links added only where they exist (missing targets noted for ③-4/5/6 tasks)
- [ ] 4.2 Add `e2e/docs/test_basic_*.py` per page (title, TOC populated, no console errors; prod + static)
- [ ] 4.3 Spot-check every code block against current APIs (component names resolve, filter list matches registry)
- [ ] 4.4 `uv run ruff check .` + `uv run ruff format --check .` + `uv run pyright` + `uv run python -m pytest tests/ --tb=short`
- [ ] 4.5 `uv run python -m webcompy generate` + docs E2E groups; `python3 scripts/check-doc-spec-refs.py`; `openspec validate feat-docs-basic-usage`
