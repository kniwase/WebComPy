# Tasks: Remove hidden attribute from prerendered app root

- [ ] **Task 1: Remove hidden override in AppRootComponent._render_html()**

**Estimated time: ~0.5 hours**

### Steps

1. Open `webcompy/app/_root_component.py`.
2. Remove the `_render_html()` method from `AppRootComponent` (lines 182-190). The inherited implementation from `ElementWithChildren` respects the actual attribute state.
3. Verify that `prerender=True` output no longer includes `hidden` on `#webcompy-app`.
4. Verify that `prerender=False` output still includes `hidden` on `#webcompy-app` (handled by `generate_html()`).

### Acceptance Criteria

- `prerender=True` HTML output has `#webcompy-app` without `hidden`.
- `prerender=False` HTML output has `#webcompy-app` with `hidden`.
- All existing tests pass.
- Pre-rendered content is visible beneath the semi-transparent loading screen.

---

- [ ] **Task 2: Add unit test for prerender output without hidden**

**Estimated time: ~0.5 hours**

### Steps

1. Add a test that generates HTML with `prerender=True` and asserts `#webcompy-app` lacks `hidden`.
2. Add a test that generates HTML with `prerender=False` and asserts `#webcompy-app` has `hidden`.
3. Run E2E tests to confirm `test_loading_screen_removed` still passes.

### Acceptance Criteria

- Unit tests cover both prerender modes.
- E2E tests pass.