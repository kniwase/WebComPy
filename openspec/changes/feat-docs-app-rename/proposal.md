## Why

The documentation site directory is currently named `docs_src`, which does not clearly convey that it is a runnable WebComPy application. Renaming it to `docs_app` aligns with the project's naming conventions (the E2E test app is `my_app`) and makes the directory's purpose as a self-contained application more explicit. Additionally, the Fetch Sample demo page is broken because it references a `sample.json` static file that does not exist, and the app has no `static` directory configured.

## What Changes

- **BREAKING**: Rename `docs_src/` directory to `docs_app/`, updating all import paths, configuration references, CLI commands, and CI workflows that reference the old name
- Fix the Fetch Sample demo by adding `docs_app/static/fetch_sample/sample.json` with test data
- Update `docs_app/webcompy_server_config.py` to include `static_files_dir="static"` so the dev server and SSG serve the static directory
- Update all references in CI workflows (`ci.yml`, `deploy-pages.yml`) from `docs_src` to `docs_app`
- Update `AGENTS.md` references from `docs_src` to `docs_app`

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `cli`: Update documentation and config references from `docs_src` to `docs_app`
- `app-config`: Configure `static_files_dir` for docs_app server and generator

## Impact

- **Directory rename**: `docs_src/` → `docs_app/` — all Python imports, CLI commands, and file references must be updated
- **CI workflows**: `ci.yml` and `deploy-pages.yml` must reference `docs_app` instead of `docs_src`
- **AGENTS.md**: Dev server and SSG commands must reference `docs_app.bootstrap:app`
- **Fetch Sample**: Will work correctly after adding `sample.json` and configuring `static_files_dir`

## Known Issues Addressed

_(none)_

## Non-goals

- Adding E2E tests for the docs_app — that is covered by the `feat-docs-e2e` change
- Changing the E2E test app (`my_app`) naming or structure
- Modifying any component or page behavior beyond the Fetch Sample fix