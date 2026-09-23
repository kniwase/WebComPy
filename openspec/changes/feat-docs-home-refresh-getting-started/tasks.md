# Tasks: feat-docs-home-refresh-getting-started

## 1. Home refresh

- [x] 1.1 Restructure `docs_app/templates/home.py`: hero band (h1 + subtitle + Get Started / View on GitHub buttons), feature-cards band (4 `DocsCard` tiles), teaser band (uv one-liner + first-component snippet + Installation link), footer band; delete Poetry blocks and Lock File Commands table
- [x] 1.2 Add `".code-block": {"margin": "var(--space-4) 0"}` to `Home` scoped style; verify computed rhythm against `.prose pre` in a browser check
- [x] 1.3 Update `e2e/docs/test_home.py` to the new structure (hero heading, Get Started link, absence of Poetry block)

## 2. Getting Started orientation pages

- [x] 2.1 Write `docs_app/documents/what_is_webcompy.md` (positioning, dual-environment model, core promises, FastAPI relationship) + thin page wrapper + manifest entry `/documents/getting-started/what-is-webcompy`
- [x] 2.2 Write `docs_app/documents/why_webcompy.md` (Why list + honest Why-not list incl. PyScript payload/cold start, young ecosystem) + wrapper + manifest entry
- [x] 2.3 Write `docs_app/documents/project_structure.md` (app package, config split build vs server, static/, resources, lockfile) + wrapper + manifest entry
- [x] 2.4 Reorder Getting Started entries: what-is → why → installation → quickstart → project-structure

## 3. Existing page revisions

- [x] 3.1 `installation.md`: update config snippet to scaffold-template shape (incl. `server=WebComPyServerConfig`, explained fields), clarify optional browser deps, expand headings for TOC, keep git+ URL "until PyPI" note
- [x] 3.2 `quickstart.md`: switch example to `@define_component()` derived form, mention `custom_element_name=` for non-derivable tags, fix Installation link to current path
- [x] 3.3 `custom_elements.md`: replace round-trip validation text with the optional-derivation contract (#286)
- [x] 3.4 Sweep all `docs_app/documents/*.md` for old `@define_component("<name>")` examples; convert to derived form where derivable

## 4. Tests & verification

- [x] 4.1 Add E2E files for the three new pages (title, TOC, no console errors; prod + static)
- [x] 4.2 `uv run ruff check .` + `uv run ruff format --check .` + `uv run pyright` + `uv run python -m pytest tests/ --tb=short`
- [x] 4.3 `uv run python -m webcompy generate` + docs E2E group run
- [x] 4.4 `python3 scripts/check-doc-spec-refs.py` + `openspec validate feat-docs-home-refresh-getting-started`

## 5. Review follow-ups

- [x] 5.1 Fix Home teaser to match canonical install steps (all three `uv add` lines, `mkdir` form)
- [x] 5.2 Use `RouterLink` for Home internal links + SPA proof E2E test
- [ ] 5.3 Restore Home-based no-duplicated-install-detail test
- [ ] 5.4 Tag ASCII-diagram fences as `text`; drop dead `.commands-table` CSS
- [ ] 5.5 Sync spec/design wording for home code-block spacing to docs_app stylesheet approach
- [ ] 5.6 Full verification (lint, type, unit, generate, docs E2E)
