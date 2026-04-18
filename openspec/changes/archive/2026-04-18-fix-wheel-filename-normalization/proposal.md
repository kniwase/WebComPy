## Why

The `_normalize_name()` function in the wheel builder uses hyphens for package name normalization (e.g., `docs_src` → `docs-src`), which produces wheel filenames like `docs-src-26.108.34045-py3-none-any.whl`. PEP 427 specifies that the distribution name component in wheel filenames must use underscores as separators, not hyphens. Hyphens in the name conflict with the hyphen that delimits the version field, causing micropip (PyScript's package installer) to parse `docs-src-26.108.34045-py3-none-any` as name=`docs`, version=`src-26.108.34045`, which fails with `InvalidVersion: Invalid version: 'src'`. This makes the deployed site at webcompy.net completely non-functional.

## What Changes

- Fix `_normalize_name()` in `_wheel_builder.py` to use underscores instead of hyphens per PEP 427
- Update the wheel builder spec to reflect the correct PEP 427-conformant filename format
- Ensure the `.dist-info` directory name also uses underscores for the name component (already correct per PEP 427)

## Capabilities

### New Capabilities

_None_

### Modified Capabilities

- `wheel-builder`: Fix the bundled wheel naming requirement to use PEP 427-conformant underscores in the distribution name component of wheel filenames

## Impact

- `webcompy/cli/_wheel_builder.py` — `_normalize_name()` function
- `openspec/specs/wheel-builder/spec.md` — Scenario "Bundled wheel naming"
- Any code that imports or calls `_normalize_name()` directly (internal only, no public API change)
- The wheel filename format changes for ALL packages with hyphens or underscores in their names (e.g., `docs_src` → `docs_src-...whl` instead of `docs-src-...whl`). Pure alphabetic names (e.g., `myapp`) are unaffected.