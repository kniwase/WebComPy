## 1. Spike A: Single-File Module Detection Experiment

- [x] 1.1 Write throwaway patch for `_discover_packages()` to detect single `.py` files
- [x] 1.2 Write throwaway patch for `_collect_package_files()` to bundle them as top-level `{name}.py`
- [x] 1.3 Run `webcompy generate` and verify `six.py` appears at wheel root level

## 2. Spike B: Preload Timing Experiment

- [x] 2.1 Write throwaway patch: move browser preload out of `_on_set_parent()`
- [x] 2.2 Write throwaway patch: add preload in `_render()` after loading-screen removal
- [x] 2.3 Verify generated wheel contains both changes

## 3. Spike C: Error Handling Experiment

- [x] 3.1 Write throwaway patch for `_lazy.py` (`_resolve_error` flag + try/except)
- [x] 3.2 Write throwaway patch for `_router.py` (`contextlib.suppress` in closure)
- [x] 3.3 Verify generated wheel contains error handling code

## 4. Implementation: Wheel Builder

- [ ] 4.1 Apply single-file `.py` detection to `_discover_packages()` in `_wheel_builder.py`
- [ ] 4.2 Apply single-file handling to `_collect_package_files()` in `_wheel_builder.py`
- [ ] 4.3 Verify: all existing tests pass, `six.py` bundled correctly in generated wheel

## 5. Implementation: Router Preload Timing

- [ ] 5.1 In `_view.py`, restrict browser preload (only non-browser calls `preload_lazy_routes()` in `_on_set_parent()`)
- [ ] 5.2 In `_root_component.py`, schedule `preload_lazy_routes()` after loading-screen removal
- [ ] 5.3 Verify: all existing tests pass, generated wheel correct

## 6. Implementation: Error Handling

- [ ] 6.1 In `_lazy.py`, add `_resolve_error` flag and wrap `_preload()` with try/except
- [ ] 6.2 In `_router.py`, wrap `_do_preload` with `contextlib.suppress(Exception)`
- [ ] 6.3 Verify: all existing tests pass, generated wheel contains error handling

## 7. Final Validation

- [ ] 7.1 Run `ruff check` — must pass
- [ ] 7.2 Run `pyright` — no new errors
- [ ] 7.3 Run full test suite — all pass
- [ ] 7.4 Browser E2E: 2nd access (cached runtime) does not crash
