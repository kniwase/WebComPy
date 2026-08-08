# Tasks

## 1. Spike: verify `storage` event reception from PyScript (GATE — abort conditions apply)

- [x] 1.1 Add a temporary spike page to the e2e app (`e2e/core/my_app/pages/`) that registers a `storage` listener via `create_proxy` + `addEventListener` and records received events (`key`, `newValue`, `url`) into the DOM
- [x] 1.2 Write a Playwright verification script that opens TWO pages in ONE browser context (separate contexts do not share `localStorage`), writes/removes from page B, and asserts page A's records
- [x] 1.3 Verify the six spike items (design "Spike Gate"): (1) event reception, (2) payload readability, (3) writing tab does not receive its own event, (4) same-value `setItem` firing behavior, (5) `removeItem`/`clear()` payload shape, (6) clean detach via `removeEventListener` + `proxy.destroy()`
- [x] 1.4 Record findings in design.md "Spike Findings". **If item 1, 2, or 6 fails: STOP. Do not proceed to section 2+. Record evidence, discard the change, and keep cross-tab sync as a documented non-goal of storage persistence.**
- [x] 1.5 On success, keep the spike script as the basis of the permanent e2e test (section 4)

## 2. Implementation (only after the spike gate passes)

- [x] 2.1 Add keyword-only `sync_tabs: bool = False` to `use_local_storage` (both overloads); `use_session_storage` unchanged (design D4)
- [x] 2.2 Implement the shared-listener + key registry with per-app scoping per design D1 (DI key or per-app holder following existing patterns; NO module-global singleton)
- [x] 2.3 Implement the remote-apply path with the `_applying_remote` flag guarding `_write` (design D2); removal → reset to default (D3); corrupted payload → warning + default
- [x] 2.4 Listener lifecycle: `create_proxy` / `removeEventListener` / `destroy` per framework invariant; subscriber unregister on component destroy for setup-created instances
- [x] 2.5 Server no-op path (`ENVIRONMENT != "pyscript"`)

## 3. Unit tests

- [x] 3.1 Fake-dispatch tests (no browser): remote write updates signal + notifies consumers; remote removal resets (value and factory defaults); corrupted payload warning; unregistered key ignored; no write-back during apply (assert fake storage `setItem` not called); equal-value delivery is a no-op
- [x] 3.2 `sync_tabs=False` registers nothing; server path creates no listener
- [x] 3.3 Registry scoping: two app instances do not share subscriptions; unregister on destroy

## 4. E2E and docs

- [x] 4.1 Convert the spike script into a permanent e2e test: two tabs, write in B → assert A's UI updates; remove in B → assert A resets
- [x] 4.2 Document `sync_tabs` as OpenSpec requirements/scenarios in the composables delta spec (opt-in, localStorage only, last-writer-wins, `clear()` reset, no-DI-scope skip). The `docs_app` composables storage section does not exist, so no `docs_app` changes are made.

## 5. Verification

- [x] 5.1 `uv run ruff check .` / `uv run ruff format --check .` / `uv run pyright`
- [x] 5.2 `uv run python -m pytest tests/ --tb=short` (all existing tests MUST pass)
- [x] 5.3 Relevant e2e group via `scripts/run-e2e-tests.sh` (all groups: 32 passed, 0 failed)

## 6. Housekeeping (at archive time)

- [x] 6.1 Update `AGENTS.md` File→Spec Mapping if new modules/keys were introduced (no new modules; `webcompy/di/` row already covers `_keys.py` — no change needed)
