# Tasks

## 1. Framework Asset Hashing & Cache-Busting HTML Rewriting

- [ ] 1.1 Add `_append_asset_version()`, `_rewrite_head_link_hrefs()`, and `_rewrite_script_attrs()` helpers plus optional `asset_hashes: dict[str, str] | None = None` support on `generate_html()` in `packages/webcompy-server/src/webcompy_server/_html.py`, preserving `<style data-webcompy-cid>` placement after the versioned `/_webcompy-ui/index.css` link; verify with unit tests in `tests/test_asset_cache_busting.py`.
- [ ] 1.2 Add `_compute_asset_hashes()` and `BuildArtifacts.asset_hashes` / `framework_ui_index_css` fields in `packages/webcompy-cli/src/webcompy_cli/_build.py` (enabled only when `dev_mode=False`), hashing leaf UI CSS files before rewriting `index.css` `@import` URLs and hashing rewritten `index.css` plus `static_files_dir` files; verify with unit tests in `tests/test_asset_cache_busting.py`.
- [ ] 1.3 Wire rewritten `index.css`, `asset_hashes`, prod/dev `Cache-Control` headers on `/_webcompy-ui/*`, and prod `immutable` `Cache-Control` headers on `/_webcompy-app-package/*` and `/_webcompy-assets/packages/*` in `packages/webcompy-cli/src/webcompy_cli/_server.py` and `packages/webcompy-cli/src/webcompy_cli/_generate.py`; verify with ASGI and SSG unit tests.
- [ ] 1.4 Regenerate API docs (`uv run python scripts/generate_api_reference.py`) and document prod cache-busting / immutable asset headers in `docs_app/documents/server_serving_modes.md`; verify `generate_api_reference.py --check` and `check-docstrings.py` pass.

## 2. Docs App Inline Skip-Link & Static Hosting Headers

- [ ] 2.1 Create `docs_app/static/_headers` configuring `Cache-Control: public, max-age=31536000, immutable` for `/_webcompy-assets/*` and `/_webcompy-app-package/*`, and verify it is copied into generated `dist/_headers`.
- [ ] 2.2 Move `.skip-link`, `.skip-link:focus`, and `.skip-link:focus-visible` styles from `docs_app/static/styles/components.css` into `DocsRoot.scoped_style` (`docs_app/layout/__init__.py`); verify via unit test in `tests/test_docs_page.py` and focus geometry assertions in `e2e/docs/test_home.py`.

## 3. Full Verification & Spec Archival

- [ ] 3.1 Run `uv run ruff format --check .`, `uv run ruff check .`, `uv run pyright`, `uv run python scripts/check-docstrings.py`, `uv run python scripts/generate_api_reference.py --check`, `uv run python scripts/generate_docs_search_index.py --check`, `python3 scripts/check-doc-spec-refs.py`, `uv run python -m pytest tests/`, SSG output check on `docs_app`, and Playwright E2E (`e2e/docs/test_home.py`, `e2e/docs/test_documents.py` in `static` and `prod` modes).
- [ ] 3.2 Sync delta specs into `openspec/specs/` and archive `feat-static-asset-cache-busting`, then verify `openspec validate --specs` and `openspec validate --changes`.
