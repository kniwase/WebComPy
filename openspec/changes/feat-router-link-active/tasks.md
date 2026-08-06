# Tasks

## 1. Implementation

- [x] 1.1 Add `active_class` / `exact` kwargs to `TypedRouterLink.__init__` (`packages/webcompy/src/webcompy/router/_link.py`); store values RAW (`self._active_class`, `self._exact`); create `self._class_attr` / `self._aria_current_attr` `Computed`s when `active_class is not None` (design D1, D3)
- [x] 1.2 Implement `_target_path()` normalization and `_is_active()` matching, including trailing-slash normalization of both sides (design D2, D7: root exact, segment-boundary prefix, query stripped, `/docs/` ≡ `/docs`, `current_match is None` → False)
- [x] 1.3 Implement `_compute_class_attr()` / `_compute_aria_current_attr()` (live value read, never cached) and extend `_generate_attrs()` with `Computed` class merging and `aria-current="page"` while active (design D5, D6)

## 2. Tests

- [ ] 2.1 Unit tests via `webcompy_testing` (`tests/test_router_link_active.py`): all spec scenarios — prefix, segment boundary, root exact, trailing-slash normalization, `exact=True`, query ignored, 404 never-active, reactive toggle on `__set_path__`, reactive `active_class` signal change at runtime, SSR initial render
- [ ] 2.2 Regression: `active_class=None` renders byte-identical attrs to before (no `aria-current`, no `class` modification, no extra subscriptions)
- [ ] 2.3 User `class` as plain str merges with active class; user `class` as signal stays reactive (merged string updates on both navigation and user-class signal change)

## 3. Verification

- [ ] 3.1 Verify SSR path: first render computes active state with no browser API access
- [ ] 3.2 `uv run ruff check .` and `uv run ruff format --check .`
- [ ] 3.3 `uv run pyright`
- [ ] 3.4 `uv run python -m pytest tests/ --tb=short` (all existing tests MUST pass)
