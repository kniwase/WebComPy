## Context

Currently, `GenerateConfig.dist` and `static_files_dir` (in both `ServerConfig` and `GenerateConfig`) are resolved via `Path(value).absolute()`, which resolves relative to CWD. This is fragile — running `webcompy generate` from a different directory changes the output location. The only reason it works in practice is that developers always run from the project root, and `app_package_path` defaults to `"."` (CWD).

The template config (`webcompy_config.py`) uses `Path(__file__).parent / "app"` for `app_package`, producing an absolute path. But `dist` and `static_files_dir` remain CWD-relative, so a template project's `dist` goes to `./dist/` rather than `<app>/dist/`.

## Goals / Non-Goals

**Goals:**
- Resolve `dist` and `static_files_dir` relative to `app_package_path`, making output self-contained within the app package
- Remove the `static_files_dir_path` property from config dataclasses (it lacks the `app_package_path` context needed for correct resolution)
- Update `docs_app` to use `dist="dist"` instead of `dist="docs"`, with CI paths adjusted accordingly

**Non-Goals:**
- Changing how `app_package_path` itself is resolved
- Changing `--dist` CLI flag behavior (still CWD-relative override)
- Making `static_files_dir` aware of different app packages in multi-app setups (only the primary app's `app_package_path` is used)

## Decisions

### 1. Resolve paths at call sites, not in config dataclasses

**Decision:** Remove `static_files_dir_path` property from `ServerConfig` and `GenerateConfig`. Resolve `dist` and `static_files_dir` at the point of use in `_generate.py` and `_server.py`, where `app.config.app_package_path` is available.

**Rationale:** The config dataclasses have no access to `app_package_path`. Resolving CWD-relative paths inside a property on the config object is misleading — it looks self-contained but depends on global CWD state.

**Alternative considered:** Pass `app_package_path` into `GenerateConfig`/`ServerConfig` at construction time. Rejected because these are user-facing config objects defined in `webcompy_server_config.py`; adding an internal field breaks the clean separation.

### 2. Use `(app_package_path / value).absolute()` pattern

**Decision:** `dist_dir = (app.config.app_package_path / dist).absolute()`

**Rationale:** `pathlib.Path.__truediv__` handles absolute `value` correctly (ignores the left operand), so `--dist /tmp/out` still works. For relative values like `"dist"` or `"static"`, the join with `app_package_path` produces the correct app-relative path.

### 3. Change docs_app dist from `"docs"` to `"dist"`

**Decision:** `docs_app/webcompy_server_config.py` changes to `dist="dist"`, and `docs_app/` has no `static_files_dir` (falls back to default `"static"`, which resolves to `docs_app/static/`). CI paths change from `docs/` to `docs_app/dist/`.

**Rationale:** The `docs/` directory was a legacy choice tied to the CWD-relative behavior. With app-relative resolution, `"dist"` is the natural default and keeps generated output inside the app package.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Users with custom `webcompy_server_config.py` that rely on CWD-relative `dist` from a non-root working directory may see changed output paths | For `app_package="."` (default), behavior is identical since `app_package_path == CWD`. Only apps with explicit `app_package="subdir/"` are affected, and the new behavior is the intuitive one. |
| `_server.py` currently only uses `server_config.static_files_dir_path` and does not have a direct `app` reference at that call site | The `create_asgi_app` function already takes `app: WebComPyApp`, so `app.config.app_package_path` is available at line 236. |
