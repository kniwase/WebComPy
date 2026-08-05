# Tasks

## 1. HistoryPort hook

- [ ] 1.1 Add `ScrollManager` protocol + `set_scroll_manager()` to `ports/_history.py`; invoke `on_push` from `navigate()` after `_do_navigate` (design D1)
- [ ] 1.2 Invoke `on_pop` from `BrowserHistoryPort._on_popstate` on both dispatch paths (design D1)
- [ ] 1.3 Unit tests: push/pop classification, exactly-once, same-value early-return silence, no-manager regression

## 2. ScrollManager

- [ ] 2.1 Implement `router/_scroll.py` `BrowserScrollManager`: positions map, `on_push`/`on_pop`, `_schedule` with bounded retry (3 attempts) and clamping (design D2, D3)
- [ ] 2.2 Set `history.scrollRestoration = "manual"` in `__init__` (design D4)
- [ ] 2.3 Unit tests with fake window/host/document: save-on-push, save-on-pop, restore, top-on-first-visit, retry-until-tall-enough, give-up-clamps, short-page no-retry

## 3. Wiring and config

- [ ] 3.1 Add `scroll_restoration: bool = True` to `WebComPyAppConfig` (`app/_config.py`)
- [ ] 3.2 Instantiate + register `BrowserScrollManager` where the browser `HistoryPort` is provisioned, gated on `ENVIRONMENT == "pyscript"` and the config flag (design D4); verify SSR/SSG create nothing

## 4. E2E and docs

- [ ] 4.1 E2E: long page → scroll → navigate → assert top → Back → assert restored (add page under `e2e/core/my_app/pages/` + Playwright spec)
- [ ] 4.2 Document default behavior + opt-out in `docs_app` routing page; verify `uv run python -m webcompy generate`

## 5. Verification

- [ ] 5.1 `uv run ruff check .` / `uv run ruff format --check .` / `uv run pyright`
- [ ] 5.2 `uv run python -m pytest tests/ --tb=short` (all existing tests MUST pass)
- [ ] 5.3 Relevant e2e group via `scripts/run-e2e-tests.sh`

## 6. Housekeeping (at archive time)

- [ ] 6.1 Update `AGENTS.md` File→Spec Mapping (`webcompy/router/_scroll.py` → `scroll-restoration`; `ports/_history.py` → `port-abstraction` + `scroll-restoration`) and Current Specs list
