# Tasks: feat-docs-guides-tutorial

## 1. Tutorial demo apps

- [x] 1.1 Scaffold `docs_app/static/_demos/todo_tutorial/step1..step6/app.py` (standalone apps, progressive feature sets per the design curriculum table) and register `"todo_tutorial/step1": []` .. `"todo_tutorial/step6": []` in `standard.html`'s app map
- [x] 1.2 Step 5: implement the `/api/tasks` in-memory mock via `add_fetch_middleware(...)` inside root component setup (`GET` list + `POST` add + `PATCH` toggle); verify no network in static or prod mode
- [x] 1.3 Manual pass: verify all tutorial pages and demo iframes render with zero console errors via `webcompy inspect`

## 2. Pages

- [x] 2.1 Write `docs_app/documents/guides_overview.md` (what you build, step list, prerequisites) + wrapper + manifest entry
- [x] 2.2 Write step pages `guides_step1_state.md` … `guides_step6_deploy.md` per the page shape (lead + narrative + Next steps + `DemoDisplay` via `extra_content`); 7 files total
- [x] 2.3 Insert the `Guides` section into `DOCS_SECTIONS` between Getting Started and Basic Usage; add thin page wrappers

## 3. Verification

- [x] 3.1 `e2e/docs/test_guides_tutorial.py`: overview & every step page title + demo iframe loads + step-5 mocked submit updates the list with zero `/api/tasks` network requests (prod + static), wired into the `docs-documents` group in `scripts/run-e2e-tests.sh` and `.github/workflows/ci.yml`
- [x] 3.2 `uv run ruff check .` + `uv run ruff format --check .` + `uv run pyright` + `uv run python -m pytest tests/ --tb=short`
- [x] 3.3 `uv run python -m webcompy generate` (dist contains demo apps) + `docs-documents` (static + prod) and `docs-demos` (static) E2E groups
- [x] 3.4 `python3 scripts/check-doc-spec-refs.py` + `openspec validate feat-docs-guides-tutorial`
