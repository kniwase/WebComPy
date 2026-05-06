## 1. Core path resolution changes

- [ ] 1.1 Remove `static_files_dir_path` property from `ServerConfig` and `GenerateConfig` in `webcompy/app/_config.py`
- [ ] 1.2 In `webcompy/cli/_generate.py`, resolve `dist` relative to `app.config.app_package_path`: change line 173 from `pathlib.Path(dist).absolute()` to `(app.config.app_package_path / dist).absolute()`
- [ ] 1.3 In `webcompy/cli/_generate.py`, resolve `static_files_dir` relative to `app.config.app_package_path`: change line 187 from `generate_config.static_files_dir_path.absolute()` to `(app.config.app_package_path / generate_config.static_files_dir).absolute()`
- [ ] 1.4 In `webcompy/cli/_server.py`, resolve `static_files_dir` relative to `app.config.app_package_path`: change line 236 from `server_config.static_files_dir_path.absolute()` to `(app.config.app_package_path / server_config.static_files_dir).absolute()`

## 2. Update tests for path resolution change

- [ ] 2.1 Update `tests/test_config_dataclasses.py` to remove assertions about `static_files_dir_path` property
- [ ] 2.2 Update `tests/test_config_discovery.py` to verify `GenerateConfig` and `ServerConfig` no longer have `static_files_dir_path` property
- [ ] 2.3 Run existing test suite to catch any other references to `static_files_dir_path`

## 3. docs_app configuration update

- [ ] 3.1 Change `dist` from `"docs"` to `"dist"` in `docs_app/webcompy_server_config.py`

## 4. CI and gitignore updates

- [ ] 4.1 Update `.github/workflows/ci.yml`: change `path: docs/` to `path: docs_app/dist/` in both artifact upload and download steps
- [ ] 4.2 Update `.github/workflows/ci.yml`: change `DOCS_DIST_DIR: .../docs` to `.../docs_app/dist`
- [ ] 4.3 Update `.github/workflows/deploy-pages.yml`: change `path: ./docs` to `path: ./docs_app/dist`
- [ ] 4.4 In `.gitignore`, remove `/docs/` entry and add `docs_app/dist/`

## 5. Verification

- [ ] 5.1 Run `uv run python -m webcompy generate --app docs_app.bootstrap:app` and verify output goes to `docs_app/dist/`
- [ ] 5.2 Run `uv run ruff check .` for lint
- [ ] 5.3 Run `uv run pyright` for type check
- [ ] 5.4 Run `uv run python -m pytest tests/ --tb=short` and ensure all tests pass
