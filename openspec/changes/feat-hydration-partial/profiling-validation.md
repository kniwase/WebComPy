# Profiling Validation: feat-hydration-partial

## Environment

- Date: 2026-04-23
- Branch: feat/hydration-partial
- App: docs_src (profile=True)

## Verification Results

### 1. Generated HTML contains profiling bootstrap code

When `AppConfig(profile=True)` is set, the generated HTML includes:
- `import time` in PyScript bootstrap
- `_pyscript_ready = time.perf_counter()` timing capture
- `app._profile_data["pyscript_ready"]` assignment before `app.run()`

**Result: PASS** — Profiling bootstrap code is present in generated HTML.

### 2. Semi-transparent loading screen in generated HTML

The `_Loadscreen._style` now includes `background: rgba(0, 0, 0, 0.5)` on the `.container` element, making the pre-rendered content visible beneath the loading overlay.

**Result: PASS** — `rgba(0, 0, 0, 0.5)` is present in generated HTML.

### 3. Unit tests for conditional DOM writes

All 8 new tests in `TestPartialHydrationTextElement` and `TestPartialHydrationElement` pass:
- Text write skipped when content matches
- Text write performed when content differs
- Signal-based text comparison works correctly
- Attribute setAttribute skipped when values match
- Attribute setAttribute performed when values differ
- Stale attributes removed (value=False)
- Extra attributes not in component are removed
- New elements unconditionally set attributes

**Result: PASS** — 8/8 tests passed.

### 4. E2E tests pass with partial hydration changes

Running `test_bootstrap.py` against the prod server (port 8088):
- `test_app_loads`: PASS
- `test_loading_screen_removed`: PASS
- `test_home_page_rendered`: PASS
- `test_page_title`: PASS

**Result: PASS** — 4/4 E2E tests passed.

### 5. Profiling unit tests

All 14 existing profiling tests continue to pass.

**Result: PASS** — 14/14 tests passed.

## Summary

The partial hydration optimization (skipping redundant `setAttribute` and `textContent` writes on prerendered nodes) is correctly implemented. No before/after performance comparison is available on this branch since the optimization is already applied. The change is structurally correct: DOM reads (`getAttribute`, `textContent` getter) are always cheaper than DOM writes (`setAttribute`, `textContent` setter), and for SSG-hydrated pages where all values match, 100% of redundant writes are eliminated.

The semi-transparent loading screen (`rgba(0, 0, 0, 0.5)`) is verified in the generated HTML, allowing users to see pre-rendered content during hydration.