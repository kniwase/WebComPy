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

## 6. AI review follow-ups (round 3)

- [x] 6.1 RenderContext dispose unwinding: walk the active DI scope's parent chain and reset `_active_di_scope` whenever it belongs to the disposed tree (root or descendant), leaving foreign live scopes untouched
- [x] 6.2 Payload closure for non-hydrating apps: close `_hydration_payload_closed` right after the initial child render (before loading teardown / lazy-route preload) regardless of `_hydrate`; drain + mismatch summary stay on the hydrating path only
- [x] 6.3 Suspense DI-scope snapshot before probing: capture `original_scope` before probe-children generation; use `_restore_suspense_di_scope` on the hydration fast path; pass the pre-captured scope into `_browser_resolve` (also from `_browser_render`)
- [x] 6.4 Provisional transfer ordinals: probe-depth mode on `RenderContext._next_transfer_id` gives the hydration fallback non-consuming ids so per-name counters stay aligned with the SSR tree
- [x] 6.5 Timeout probe destruction: destroy the discarded probe subtree (destroy hooks, effect scopes, child DI scopes) on the deferred-resolution timeout while keeping the live fallback
- [x] 6.6 Tests for 6.1–6.5 (dispose with active child/grandchild scope, foreign-scope no-op, non-hydrating closure before fade, fast-path + deferred probe scope restore, provisional-transfer-id alignment, timeout destroy)
- [x] 6.7 Spec sync: `di-scope` (dispose unwinding), `hydration-data-transfer` (window closes before loading teardown in all browser modes), `suspense` (pre-probe snapshot, provisional ordinals, timeout teardown)

## 7. AI review follow-ups (round 4)

- [x] 7.1 Deferred Suspense caller restore: `_browser_render` and `_hydrate_node` restore `original_scope` immediately after probe generation and after fallback generation before scheduling, so `provide()` inside the probe does not leak into fallback or caller
- [x] 7.2 DIScope context manager: restore `DIScope.__exit__` to unconditional `reset(token)` (with `try/except` fallback) so a `with` block containing `provide()` correctly restores the previous scope
- [x] 7.3 Probe teardown single-owner: timeout, cancellation, and error paths destroy the discarded probe subtree via a single recursive `_remove_element` loop without a separate `_cleanup_pending_pairs` call, keeping the live fallback untouched and avoiding double `on_before_destroy`
- [x] 7.4 SSR provisional fallback: `_server_render` timeout fallback wrapped in `_transfer_probe_depth` provisional guard so SSR and browser fallback ordinals align
- [x] 7.5 Dispose chain walking: `RenderContext` stores `_prev_active_app_context` / `_prev_render_context_cv` / `_prev_active_di_scope` and `dispose()` walks past disposed predecessors to the next live context for all three bindings (`_active_app_context`, `_render_context_cv`, `_active_di_scope`)
- [x] 7.6 Tests for 7.1–7.5 (caller leak after probe, DIScope leak after provide, timeout single-owner, SSR provisional ordinal, three-context walk) — existing suites extended, no new `Note` item (payload-inject-before-window skipped as low value per plan)
- [x] 7.7 Spec sync: `di-scope` (context-manager descendant restore, three-context walk), `suspense` (caller restore, single-owner teardown, cancellation, SSR provisional)
