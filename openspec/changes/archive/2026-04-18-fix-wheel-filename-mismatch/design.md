## Context

The wheel builder (`_wheel_builder.py`) produces bundled wheels whose filename is derived from the normalized app package name (e.g., `docs-src-25.108.52740-py3-none-any.whl` for a package named `docs_src`). However, the HTML template (`_html.py`) hardcodes the wheel URL as `app-{version}-py3-none-any.whl`. This mismatch was introduced when the two-wheel design (separate `webcompy` + `app` wheels) was replaced with a single bundled wheel — the HTML template was never updated to reflect the new naming.

The dev server (`_server.py`) is also affected: it stores wheels in an in-memory dict keyed by actual filename, and the route handler looks up the URL's filename in that dict. Since the URL and filename diverge, the lookup fails.

Current data flow:

```
make_webcompy_app_package(name=package_dir.name, ...)
  → make_bundled_wheel(name=package_dir.name, ...)
    → dist_name = _normalize_name(package_dir.name)  # e.g. "docs-src"
    → wheel filename = "docs-src-{ver}-py3-none-any.whl"

generate_html(...)
  → py_packages URL: "{base}_webcompy-app-package/app-{ver}-py3-none-any.whl"
                                                      ^^^ hardcoded
```

## Goals / Non-Goals

**Goals:**
- Ensure the wheel filename referenced in HTML matches the actual filename produced by the wheel builder
- Establish a single source of truth for wheel filename computation, used by the builder, HTML generator, dev server, and static generator
- Fix the `BadZipFile` error for all app package names (not just `app`)

**Non-Goals:**
- Changing the PEP 427 normalization of distribution names in dist-info or METADATA
- Modifying how micropip/PyScript loads wheels
- Switching back to two separate wheels

## Decisions

### Decision 1: Extract `get_wheel_filename` helper into `_wheel_builder.py`

Add a public function `get_wheel_filename(name: str, version: str) -> str` that computes the PEP 427 wheel filename using the same logic as `make_bundled_wheel`. All consumers (HTML, server, generator) call this function instead of hardcoding the pattern.

**Rationale:** A single function eliminates the possibility of the filename pattern drifting between files. The `_wheel_builder.py` module already owns filename computation; extending it is natural.

**Alternatives considered:**
- Hardcode `"app"` as the wheel name in `make_webcompy_app_package` (matches old setuptools behavior) — but this creates an artificial separation between the wheel's distribution name and the app's actual name, and the METADATA `Name` field would be `app` regardless of the real package, which is misleading.
- Store the filename in `WebComPyConfig` — over-engineering; the filename is deterministic from the app name and version.

### Decision 2: Pass `app_name` and `app_version` to `generate_html`

Currently, `generate_html` receives only `config` and `app_version`. It needs the app package name to compute the wheel filename. Rather than computing the filename outside and passing the URL string, pass the app package name so the function can call `get_wheel_filename` internally.

This keeps the responsibility of URL construction inside `generate_html` (where the rest of the PyScript config is built) while using the canonical filename computation.

### Decision 3: Update `make_webcompy_app_package` to return the wheel filename

`make_webcompy_app_package` currently returns `pathlib.Path` (the wheel file path). The callers (server, generator) need the filename to build URL mappings and route keys. Since they already receive the Path, they can extract the filename. No API change needed at this level.

## Risks / Trade-offs

- **[Minor API change]** `generate_html` now requires `app_package_name: str` — this is a breaking change to an internal function. Callers (`_server.py`, `_generate.py`) must be updated. Since these are all internal CLI modules, this is acceptable.
- **[Filename varies by app name]** Wheels for different apps will have different filenames. This is correct and expected — the old hardcoded `app-{version}` was hiding a bug. Cache-busting via the version timestamp already prevents stale file issues.
- **[PEP 427 normalization]** If an app package name contains dots or mixed case, the wheel filename will use hyphens and lowercase (e.g., `My.App` → `my-app-...`). This is per spec and expected.

## Migration Plan

1. Add `get_wheel_filename` to `_wheel_builder.py`
2. Update `_html.py` to use `get_wheel_filename` instead of hardcoded `app-{version}`
3. Update `_server.py` to use the actual wheel filename for both the file map and HTML generation
4. Update `_generate.py` similarly (pass app package name to `generate_html`)
5. No rollback needed — this is a direct fix, not a feature flag change