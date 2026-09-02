# Tasks: refactor-docs-sections-restructure

## 1. Manifest restructure

- [x] 1.1 Re-title `DOCS_SECTIONS` to `Getting Started` / `Basic Usage` / `Advanced Usage` and assign each of the 15 guide pages per the design mapping table (paths `…/basic/…` and `…/advanced/…`; labels and `source` unchanged)
- [x] 1.2 Extend manifest validation: page paths must carry their category prefix; unit tests for a violating path fixture and boundary order (first page Installation, last page Progressive Web App)

## 2. Body link fixes

- [x] 2.1 Convert the three relative `.md` links (`rpc.md` See-also, `rpc_websocket.md` list ×2) to rendered-site URLs with new paths
- [x] 2.2 Update all existing `/documents/...` cross-links in `docs_app/documents/*.md` to the new category paths (including the heading-anchor link in `typed_realtime.md` and the Installation link in `quickstart.md`)
- [x] 2.3 Add a unit test that scans every `docs_app/documents/*.md` for link targets ending in `.md` and fails on any hit

## 3. Tests follow

- [ ] 3.1 Update `e2e/docs/` navigation paths for all moved pages; keep group names unchanged
- [ ] 3.2 Update any unit/E2E test referencing old flat `/documents/<page>` URLs (search for `/documents/` literals)

## 4. Verification

- [ ] 4.1 `uv run ruff check .` + `uv run ruff format --check .` + `uv run pyright`
- [ ] 4.2 `uv run python -m pytest tests/ --tb=short`
- [ ] 4.3 `uv run python -m webcompy generate` on docs_app; confirm generated `dist/` contains only new category paths and old flat paths are absent (404)
- [ ] 4.4 `scripts/run-e2e-tests.sh docs-documents` (prod + static)
- [ ] 4.5 `python3 scripts/check-doc-spec-refs.py` + `openspec validate refactor-docs-sections-restructure`
