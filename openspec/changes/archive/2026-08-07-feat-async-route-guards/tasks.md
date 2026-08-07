# Tasks

## 1. HistoryPort URL ownership

- [x] 1.1 Add `push_url` / `replace_url` no-op methods to `HistoryPort` (`ports/_history.py`); add recording overrides to `webcompy_testing` fakes (design D4)
- [x] 1.2 Implement both in `BrowserHistoryPort` (`ports/_browser/_history.py`) with optional `base_url` ctor param; hash `#` prefix / history base_url prefix; non-serializable state → `None` + warning (logic moved from `_link.py:104-110`)
- [x] 1.3 Thread `base_url` through the browser port provisioning site
- [x] 1.4 Unit tests: URL building per mode, no-op on server ports, fake recording

## 2. Guard pipeline

- [x] 2.1 Rewrite `Router.__set_path__` into `_attempt` / `_continue_async` / `_commit` / `_interpret` with monotonic navigation token and redirect depth bound 10 (design D2, D3); sync fast-path MUST remain fully synchronous
- [x] 2.2 Guard exceptions (sync + async) → cancel + `on_route_error`, unsuppressed async → async error pipeline (design D8)
- [x] 2.3 Normalize incoming paths (base_url strip + hash `#` removal) before guard invocation (design D5)
- [x] 2.4 `_clone_for_request` gets a fresh token counter (per-request isolation)
- [x] 2.5 Remove the manual `pushState` block from `RouterLink._on_click` (`router/_link.py:92-113`); keep shape validation

> Note: popstate navigations now route through the dedicated `Router._on_browser_navigation`
> entry (no guards, no URL writes, after_route_change fires) per the approved design amendment.

## 3. Tests

- [x] 3.1 Sync matrix: allow/cancel/short-circuit unchanged; `after_route_change` fires before `__set_path__` returns (fast-path synchronicity)
- [x] 3.2 Async matrix: awaitable allow/cancel/redirect; deferred `after_route_change`
- [x] 3.3 Redirect: target guard chain re-runs; `replace_url` used; depth > 10 → `WebComPyRouterException` via `on_route_error`
- [x] 3.4 Latest-wins: pending nav A + nav B → A's continuation abandons (no URL, no signal, no after hooks)
- [x] 3.5 URL ownership: cancelled link navigation leaves address bar untouched; programmatic `set_path` pushes URL
- [x] 3.6 Guard exception routing (sync raise, async raise, suppressed via `on_route_error`)

## 4. E2E and docs

- [x] 4.1 E2E: protected page + async auth guard → redirect to `/login`; address bar shows `/login`; Back does not loop (`e2e/core/`)
- [x] 4.2 Docs: guard examples (async auth, login redirect) on the `docs_app` router page; `uv run python -m webcompy generate` succeeds
  - Docs content skipped per user decision (no router docs page exists in docs_app); `webcompy generate` success is covered in verification (step 5).

## 5. Verification

- [x] 5.1 `uv run ruff check .` / `uv run ruff format --check .` / `uv run pyright`
- [x] 5.2 `uv run python -m pytest tests/ --tb=short` (all existing tests MUST pass — watch existing router-hooks tests for fast-path regressions)
- [x] 5.3 Relevant e2e groups via `scripts/run-e2e-tests.sh` (ALL groups, prod + static — 32/32 passed)
  - Also: `uv run python -m webcompy generate --config docs_app.webcompy_config` succeeds (docs build)
  - Also: SSR/SSG renders await pending async navigations before serialization (fix commit 385a946)
