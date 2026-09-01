# Tasks: feat-docs-guides-tutorial

## 1. Tutorial demo apps

- [ ] 1.1 Scaffold `docs_app/static/_demos/todo_tutorial/step1..step6/app.py` (standalone apps, progressive feature sets per the design curriculum table) and register all six in `standard.html`'s app map
- [ ] 1.2 Step 5: implement the `/api/tasks` in-memory mock as a component-level `FetchMiddleware` inside the demo app (GET list + POST add/toggle); verify no network in static mode
- [ ] 1.3 Manual pass: each step app boots and performs its features in the dev server (browser check)

## 2. Pages

- [ ] 2.1 Write `docs_app/documents/guides_overview.md` (what you build, step list, prerequisites) + wrapper + manifest entry
- [ ] 2.2 Write step pages `guides_step1_state.md` … `guides_step6_deploy.md` per the page shape (lead + DemoDisplay + narrative + full source CodeBlock); one page per task tick, 7 files total
- [ ] 2.3 Insert the `Guides` section into `DOCS_SECTIONS` between Getting Started and Basic Usage; add thin page wrappers

## 3. Verification

- [ ] 3.1 `e2e/docs/test_guides_tutorial.py`: every step page title + demo iframe loads + step-5 mocked submit updates the list (prod + static)
- [ ] 3.2 `uv run ruff check .` + `uv run ruff format --check .` + `uv run pyright` + `uv run python -m pytest tests/ --tb=short`
- [ ] 3.3 `uv run python -m webcompy generate` (dist contains demo apps) + docs E2E groups
- [ ] 3.4 `python3 scripts/check-doc-spec-refs.py` + `openspec validate feat-docs-guides-tutorial`
