# Tasks

## 1. Implementation

- [ ] 1.1 Add `active_class` / `exact` kwargs to `TypedRouterLink.__init__` (`packages/webcompy/src/webcompy/router/_link.py`); store resolved values; add `current_match` subscription via `_add_callback_node(... on_after_updating(self._refresh))` when `active_class is not None`; subscribe to `active_class` itself when it is a `SignalBase` (design D1, D3)
- [ ] 1.2 Implement `_target_path()` normalization and `_is_active()` matching (design D2, D7: root exact, segment-boundary prefix, query stripped, `current_match is None` → False)
- [ ] 1.3 Extend `_generate_attrs()` with class merging (plain-str merge; `Computed` wrap when user `class` is a signal) and `aria-current="page"` while active (design D5, D6)
- [ ] 1.4 Verify SSR path: first render computes active state with no browser API access

## 2. Tests

- [ ] 2.1 Unit tests via `webcompy_testing` (`tests/test_router_link_active.py`): all spec scenarios — prefix, segment boundary, root exact, `exact=True`, query ignored, 404 never-active, reactive toggle on `__set_path__`, SSR initial render
- [ ] 2.2 Regression: `active_class=None` renders byte-identical attrs to before (no `aria-current`, no `class` modification, no extra subscriptions)
- [ ] 2.3 User `class` as plain str merges with active class; user `class` as signal stays reactive

## 3. Docs

- [ ] 3.1 Add active-link section to the router page in `docs_app` (kwargs, matching rules with the `/docsx` boundary example, `aria-current` note)
- [ ] 3.2 Verify `uv run python -m webcompy generate` succeeds

## 4. Verification

- [ ] 4.1 `uv run ruff check .` and `uv run ruff format --check .`
- [ ] 4.2 `uv run pyright`
- [ ] 4.3 `uv run python -m pytest tests/ --tb=short` (all existing tests MUST pass)
