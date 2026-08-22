# Tasks: fix-hydration-payload-lifecycle

## 1. Payload lifecycle gating

- [x] 1.1 Add `_hydration_payload_closed: bool = False` to `RenderContext.__init__` and a shared open-check helper (resolving the active context via `_active_app_context.get() or _get_app_instance()`, default open without a context)
- [x] 1.2 Set the flag in `AppDocumentRoot._render()` where the hydration window closes (including the `finally` path)
- [x] 1.3 Gate `_try_resolve_payload_key()` in `signal/_composable.py` on the open check
- [x] 1.4 Gate the `HYDRATION_DATA_KEY` restore in `use_async_result()` (`components/_hooks.py`) on the open check

## 2. Per-instance transfer id

- [x] 2.1 Add per-name ordinal counters and `_next_transfer_id(name)` on `RenderContext`
- [x] 2.2 Compute `transfer_id` in `Component.__setup__` before setup runs; store on `Context._transfer_id` and `ComponentProperty["transfer_id"]` (fallback: bare `generate_id(name)` without a render context)
- [x] 2.3 Use `ctx._transfer_id` for payload lookup in `_try_resolve_payload_key()` and `use_async_result()`
- [x] 2.4 Key `signals` / `async_results` collection by `transfer_id` in `hydration/_collect.py` (fallback to `component_id` for test doubles)

## 3. Tests

- [x] 3.1 Unit: restore works while the window is open; factory runs after the window closes (use_state + use_async_result)
- [x] 3.2 Unit: two instances of the same component collect and restore independent values; transfer id keeps `component_id` (scoped CSS) untouched
- [x] 3.3 Unit: fallback to bare `generate_id(name)` when no render context is active
- [x] 3.4 E2E (docs): SPA navigation helloworld → fizzbuzz updates the code block and issues a main-frame fetch for the new demo source; initial load still restores without refetch

## 4. Verification

- [x] 4.1 `ruff check` / `ruff format --check` / `pyright` pass
- [x] 4.2 `pytest tests/` passes
- [x] 4.3 Browser re-verification of the docs demo flow (dev server + Playwright)
- [x] 4.4 `openspec validate fix-hydration-payload-lifecycle --strict` passes

## 5. AI review follow-ups (round 2)

- [x] 5.1 Browser fallback restore: `RenderContext` saves the previous `_app_instance` / `_app_di_scope` pair on creation and `dispose()` restores the last live fallback (identity-guarded) so overlapping browser contexts keep fallback resolution in either disposal order
- [x] 5.2 Fallback-chain context resolution: `AppDocumentRoot._render()` resolves its render context via `_active_app_context` → per-app `_render_context_cv` → `_app_instance` fallback at hydration start, before the reveal-gating drain, and in the `finally` block
- [x] 5.3 Suspense DI-scope restore: exit the resolution scope and deterministically restore the pre-Suspense active scope in `_server_render`, `_browser_resolve`, and `_hydrate_node` so a child `provide()` does not leak into siblings
- [x] 5.4 Tests for 5.1–5.3 (unit, both disposal orders, server + browser resolution, lost-ContextVar path)
- [x] 5.5 PR body: add the required `Issues:` entry from the template
