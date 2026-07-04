## Why

`_generate.py` calls `resolve_build_artifacts()` twice during static site generation — once directly to write static files, and again inside `create_asgi_app()` to build the HTML generator. Because `generate_app_version()` uses `datetime.now()`, the two calls can produce different wheel filenames, causing the HTML to reference wheel files that don't exist on disk. The browser request for the missing wheel returns a 404 HTML page, which micropip attempts to unzip as a wheel, producing `zipfile.BadZipFile`. This breaks both CI E2E tests in `static` mode and deployed static sites.

Separately, `generate_app_version()`'s `datetime.now()` fallback makes every build non-deterministic even when the source code hasn't changed, which is semantically incorrect and causes unnecessary cache invalidation.

## What Changes

- Add `artifacts: BuildArtifacts` field to `_ServingApp` so callers can access build results without re-resolving
- Remove the duplicate `resolve_build_artifacts()` call from `_generate.py`; use `serving.artifacts` instead
- Remove `cdn_temp_dir_obj` lifecycle management from `_generate.py` (already handled by `create_asgi_app()`)
- Replace `datetime.now()` fallback in `generate_app_version()` with `"0.0.0"` (the intermediate version is never exposed externally; the final wheel's version is the content hash from `_content_hash_wheel`)
- Remove unused `app_version` parameter from `generate_html()` and its callers

## Capabilities

### New Capabilities
<!-- None — this is a bug fix, not a new capability -->

### Modified Capabilities
- `ssg-via-ssr`: `_ServingApp` now exposes `BuildArtifacts` via `.artifacts` field; `generate_app_version()` produces a deterministic value; `app_version` is removed from `generate_html()` signature (unused parameter)

## Impact

- `packages/webcompy-cli/src/webcompy_cli/_server.py` — add `artifacts` field to `_ServingApp`, populate it in `create_asgi_app()`
- `packages/webcompy-cli/src/webcompy_cli/_generate.py` — remove standalone `resolve_build_artifacts()` call, use `serving.artifacts`, remove `cdn_temp_dir_obj` finally block
- `packages/webcompy-cli/src/webcompy_cli/_utils.py` — replace `datetime.now()` with `"0.0.0"` in `generate_app_version()`
- `packages/webcompy-server/src/webcompy_server/_html.py` — remove unused `app_version` parameter
- `openspec/specs/ssg-via-ssr/spec.md` — update to reflect `_ServingApp.artifacts` and deterministic version
