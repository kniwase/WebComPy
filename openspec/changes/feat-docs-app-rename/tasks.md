## 1. Rename Directory

- [ ] 1.1 Rename `docs_src/` to `docs_app/` (git mv to preserve history)
- [ ] 1.2 Update all Python imports inside `docs_app/` that reference `docs_src` as an absolute module path — primarily `docs_app/router.py` lazy import paths (`docs_src.pages.xxx` → `docs_app.pages.xxx`)

## 2. Fix Fetch Sample

- [ ] 2.1 Create `docs_app/static/fetch_sample/sample.json` with test user data matching the `User` TypedDict schema (`id: int`, `name: str`)
- [ ] 2.2 Add `static_files_dir="static"` to `ServerConfig` and `GenerateConfig` in `docs_app/webcompy_server_config.py`

## 3. Update References

- [ ] 3.1 Update `docs_app/webcompy_config.py` — `app_import_path` from `docs_src.bootstrap:app` to `docs_app.bootstrap:app`
- [ ] 3.2 Update `.github/workflows/ci.yml` — all `docs_src` references to `docs_app`
- [ ] 3.3 Update `.github/workflows/deploy-pages.yml` — all `docs_src` references to `docs_app`
- [ ] 3.4 Update `AGENTS.md` — dev server and generate commands from `docs_src.bootstrap:app` to `docs_app.bootstrap:app`
- [ ] 3.5 Add `webcompy-lock.json` to `.gitignore` (currently missing, causing auto-generated lock files to be tracked)
- [ ] 3.6 Search codebase for any remaining `docs_src` references and update them

## 4. Verify

- [ ] 4.1 Run `uv run python -m webcompy start --dev --app docs_app.bootstrap:app` and verify it starts correctly
- [ ] 4.2 Run `uv run python -m webcompy generate --app docs_app.bootstrap:app` and verify SSG output
- [ ] 4.3 Run `uv run ruff check .` and `uv run pyright` to verify no lint/type errors
- [ ] 4.4 Run `uv run python -m pytest tests/ --tb=short` to verify existing tests pass
