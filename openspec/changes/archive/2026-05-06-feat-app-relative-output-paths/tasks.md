## 1. Core path resolution changes

- [x] 1.1 Remove `static_files_dir_path` property from `ServerConfig` and `GenerateConfig` in `webcompy/app/_config.py`
- [x] 1.2 In `webcompy/cli/_generate.py`, resolve `dist` relative to `app.config.app_package_path`: change line 173 from `pathlib.Path(dist).absolute()` to `(app.config.app_package_path / dist).absolute()`
- [x] 1.3 In `webcompy/cli/_generate.py`, resolve `static_files_dir` relative to `app.config.app_package_path`: change line 187 from `generate_config.static_files_dir_path.absolute()` to `(app.config.app_package_path / generate_config.static_files_dir).absolute()`
- [x] 1.4 In `webcompy/cli/_server.py`, resolve `static_files_dir` relative to `app.config.app_package_path`: change line 236 from `server_config.static_files_dir_path.absolute()` to `(app.config.app_package_path / server_config.static_files_dir).absolute()`

## 2. Update tests for path resolution change

- [x] 2.1 `static_files_dir_path` was never referenced in tests — no changes needed
- [x] 2.2 Same as 2.1 — no references found
- [x] 2.3 Grep confirms zero references to `static_files_dir_path` anywhere in codebase

## 3. docs_app configuration update

- [x] 3.1 Change `dist` from `"docs"` to `"dist"` in `docs_app/webcompy_server_config.py`

## 4. CI and gitignore updates

- [x] 4.1 Update `.github/workflows/ci.yml`: change `path: docs/` to `path: docs_app/dist/` in both artifact upload and download steps
- [x] 4.2 Update `.github/workflows/ci.yml`: change `DOCS_DIST_DIR: .../docs` to `.../docs_app/dist`
- [x] 4.3 Update `.github/workflows/deploy-pages.yml`: change `path: ./docs` to `path: ./docs_app/dist`
- [x] 4.4 In `.gitignore`, remove `/docs/` entry and add `docs_app/dist/`

## 5. Verification

- [x] 5.1 Verify output goes to `docs_app/dist/` (confirmed: `docs_app/dist/index.html`, `docs_app/dist/CNAME`, etc.)
- [x] 5.2 Ruff lint check passed
- [x] 5.3 Pyright type check passed (0 errors, 1 pre-existing warning)
- [x] 5.4 771 tests passed
