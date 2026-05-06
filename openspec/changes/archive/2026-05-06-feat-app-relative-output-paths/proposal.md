## Why

`GenerateConfig.dist` and `static_files_dir` in both `ServerConfig` and `GenerateConfig` are resolved relative to the current working directory (CWD), not the app's package directory (`app_package_path`). This means every `webcompy generate` or `webcompy start` invocation is CWD-sensitive — running from a different directory silently outputs to the wrong place. It also prevents generated output from being self-contained within the app package directory.

## What Changes

- **BREAKING**: `dist` and `static_files_dir` in `GenerateConfig` / `ServerConfig` will be resolved relative to `app_package_path` instead of CWD
- Remove `static_files_dir_path` property from `ServerConfig` and `GenerateConfig` (it cannot resolve relative paths without `app_package_path` context)
- `docs_app/webcompy_server_config.py`: change `dist` from `"docs"` to `"dist"` so output is self-contained in `docs_app/dist/`
- Update `.gitignore`: remove `/docs/`, add `docs_app/dist/`
- Update CI workflows and deploy-pages workflow to reference `docs_app/dist/` instead of `docs/`

## Capabilities

### New Capabilities
<!-- None — this is a refinement of existing path resolution behavior -->

### Modified Capabilities
- `project-config`: `dist` and `static_files_dir` values in `webcompy_server_config.py` SHALL be resolved relative to `app_package_path` instead of CWD
- `app-config`: Remove `static_files_dir_path` property from `ServerConfig` and `GenerateConfig`; path resolution moves to call sites that have `app_package_path` context

## Known Issues Addressed
<!-- None — this does not relate to any known issue in openspec/config.yaml -->

## Non-goals
- Changing how `app_package_path` itself is resolved (remains `Path(app_package).absolute()`, default `"."`)
- Adding a sub-command or CLI flag to configure output paths (existing `--dist` flag remains unchanged)
- Changing the behavior of `--dist` CLI flag (it still takes a CWD-relative path and overrides config)

## Impact

- `webcompy/cli/_generate.py`: resolve `dist` and `static_files_dir` relative to `app_package_path`
- `webcompy/cli/_server.py`: resolve `static_files_dir` relative to `app_package_path`
- `webcompy/app/_config.py`: remove `static_files_dir_path` property
- `docs_app/webcompy_server_config.py`: change `dist` value
- `.gitignore`: update entries
- `.github/workflows/ci.yml`: update artifact paths
- `.github/workflows/deploy-pages.yml`: update artifact path
- `openspec/specs/project-config/spec.md`, `openspec/specs/app-config/spec.md`: update requirements
