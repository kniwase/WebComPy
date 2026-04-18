## Context

The wheel builder's `_normalize_name()` function converts package names like `docs_src` to `docs-src` using hyphens. This follows PEP 503 normalization (used in package indexes like PyPI), but wheel filenames follow PEP 427, which requires underscores in the distribution name component. Micropip (PyScript's package installer) parses wheel filenames using PEP 427 rules and splits on hyphens to separate name from version, causing `docs-src-26.108.34045-py3-none-any.whl` to be parsed as name=`docs`, version=`src-26.108.34045`, which fails.

Current call chain:

```
webcompy_config.py (app_package="docs_src")
  → config.app_package_path.name → "docs_src"
    → make_webcompy_app_package(name="docs_src", ...)
      → make_bundled_wheel(name="docs_src", ...)
        → _normalize_name("docs_src") → "docs-src"     ← BUG
          → get_wheel_filename → "docs-src-...-py3-none-any.whl"
          → .dist-info dir   → "docs-src-26.x.dist-info/"
```

The fix is in `_normalize_name()`: replace hyphens with underscores. This affects both the wheel filename and the `.dist-info` directory name inside the wheel.

## Goals / Non-Goals

**Goals:**
- Fix micropip's `InvalidWheelFilename` / `InvalidVersion` error for packages with underscores or hyphens in their names
- Ensure wheel filenames comply with PEP 427
- Keep wheel filename computation centralized in `get_wheel_filename()`

**Non-Goals:**
- Changing how package names are normalized outside of wheel filenames (e.g., for import purposes)
- Adding new tests for unrelated wheel builder functionality
- Modifying the version format or timestamp-based version generation

## Decisions

### Decision 1: Use underscores in `_normalize_name()` per PEP 427

**Choice**: Change `_normalize_name()` from `re.sub(r"[-_.]+", "-", name).lower()` to `re.sub(r"[-_.]+", "_", name).lower()`.

**Rationale**: PEP 427 states that in wheel filenames, "each component of the filename is escaped by replacing any runs of non-alphanumeric characters with `_`". Hyphens in the distribution name component are ambiguous because hyphens also delimit the version field. Underscores are unambiguous.

**Alternatives considered**:
- **Keep hyphens but add special-case logic in micropip**: Not viable — this is a framework bug, not a micropip bug. Other package installers (pip, etc.) use more sophisticated parsing that handles this, but micropip correctly follows PEP 427's simple parsing.
- **Rename the package directory from `docs_src` to `docssrc`**: Would work but is a workaround, not a fix. Any future package with underscores/hyphens would hit the same bug.

### Decision 2: Update both wheel filename and dist-info directory name

**Scope**: `_normalize_name()` is used in three places: `get_wheel_filename()` (wheel filename), `make_wheel()` (dist-info dir), and `make_bundled_wheel()` (dist-info dir). All three must use the same normalization. Since the fix is in `_normalize_name()` itself, all consumers are automatically corrected.

## Risks / Trade-offs

- **[Low Risk] Existing cached wheels**: If any browser has cached the old `docs-src-...whl` filename, it will get a 404 after the fix changes the filename. However, the version includes a timestamp (e.g., `26.108.34045`), so each build already produces a unique filename. **Mitigation**: No action needed — the version changes on every build.
- **[No Risk] Import paths**: The fix only changes the wheel filename and internal dist-info directory name. It does NOT change the actual Python package name or import paths. `docs_src` will still be importable as `docs_src`.
- **[No Risk] Public API**: `_normalize_name()` is a private function (underscore prefix). `get_wheel_filename()` is the public entry point and its return value changes from `docs-src-...whl` to `docs_src-...whl`, but this is the desired fix.