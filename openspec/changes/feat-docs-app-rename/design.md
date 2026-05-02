## Context

The documentation site directory `docs_src/` is a runnable WebComPy application that serves as the project's main showcase. It is referenced throughout the codebase — in CLI commands (`--app docs_src.bootstrap:app`), CI workflows, AGENTS.md, and import paths. The directory name `docs_src` suggests it is source material for documentation rather than a self-contained application, which is misleading.

Additionally, the Fetch Sample demo page (`/sample/fetch`) is broken because:
1. It fetches `fetch_sample/sample.json` via `HttpClient.get()`
2. The `static/` directory doesn't exist in `docs_src/`
3. `webcompy_server_config.py` doesn't configure `static_files_dir`

## Goals / Non-Goals

**Goals:**
- Rename `docs_src/` to `docs_app/` to clearly indicate it is a runnable application
- Fix the Fetch Sample demo by adding `sample.json` and configuring `static_files_dir`
- Update all references: imports, CLI commands, CI workflows, documentation

**Non-Goals:**
- Adding E2E tests for docs_app (covered by `feat-docs-e2e`)
- Changing the E2E test app (`my_app`) naming or structure
- Refactoring the Fetch Sample component logic

## Decisions

### Decision: Directory rename `docs_src` → `docs_app`

The new name `docs_app` follows the same convention as the E2E test app (`my_app`) — a Python package that is also a runnable WebComPy application. This makes the directory's purpose unambiguous.

**Alternative considered**: `docs/` — rejected because it conflicts with the generated docs output directory (also `docs/` per `GenerateConfig.dist="docs"`) and is less specific.

**Impact**: This is a breaking rename. All import paths change from `docs_src.xxx` to `docs_app.xxx`. The following must be updated:
- `docs_app/router.py` — `lazy()` calls use absolute paths that change
- `docs_app/webcompy_config.py` — `app_import_path` references `docs_src.bootstrap:app`
- `docs_app/bootstrap.py` — uses only relative imports, no changes needed
- `docs_app/pyproject.toml` — contains `[project.optional-dependencies] browser = ["numpy", "matplotlib"]` but no `docs_src` references, so no changes needed
- CI workflows (`ci.yml`, `deploy-pages.yml`)
- AGENTS.md dev server commands
- Any other references across the codebase

### Decision: Fix Fetch Sample with `sample.json` and `static_files_dir`

The fix requires two changes:
1. Create `docs_app/static/fetch_sample/sample.json` with minimal user data (2-3 entries)
2. Add `static_files_dir="static"` to `ServerConfig` and `GenerateConfig` in `docs_app/webcompy_server_config.py`

The `sample.json` data should match the structure expected by the `FetchSample` component (`User` TypedDict with `id` and `name` fields).

### Decision: Keep `GenerateConfig.dist` as `"docs"`

The `dist` output directory remains `"docs"` (which is gitignored). Only the source directory name changes.

## Risks / Trade-offs

- **[Import path breakage]** → All `docs_src` absolute imports must be found and updated. A grep search will catch these, but runtime testing is essential.
- **[CI workflow breakage]** → The `ci.yml` generate step and `deploy-pages.yml` both reference `docs_src.bootstrap:app`. Must be updated atomically.
- **[Lock file auto-generation]** → `docs_app/webcompy-lock.json` does not exist and will be auto-generated on first `webcompy start`. This is the same behavior as before (no lock file in `docs_src/` either). `webcompy-lock.json` must be added to `.gitignore` (currently missing, which caused past auto-generated lock files to be accidentally committed).