# Design: fix-hydration-payload-lifecycle

## Context

See proposal.md - Why. Verified in browser (docs_app dev server + Playwright):

- `/sample/helloworld` SSR payload contains `signals[md5("DemoDisplay")]["docs_app.components.demo_display:22:18"] = <helloworld source>`.
- After SPA navigation to `/sample/fizzbuzz`, the new `DemoDisplay` restores that stale entry (payload never expires, key is name-based), and `DemoDisplay.load()`'s early-return guard suppresses the refetch. No main-frame request for the new demo source is ever issued.
- Starting from `/` (no `DemoDisplay` in payload) makes the same navigations work correctly, confirming the gating condition.

Existing infrastructure this design builds on:

- `RenderContext._hydration_in_progress` already brackets the hydration window for mismatch reporting (`AppDocumentRoot._render()` sets it before hydrating/rendering children and resets it in a `finally`).
- `generate_id(component_name)` (MD5 of the component name) doubles as the scoped-CSS attribute suffix (`webcompy-cid-*`), so it cannot become instance-unique.
- `component_id` in `ComponentProperty` feeds payload collection (`hydration/_collect.py`) and diagnostics (`_suspense.py`, hydration reports).

## Goals / Non-Goals

**Goals:**

- Transfer payloads restore values only during the initial hydration window; every component setup after that runs factories.
- Multiple instances of the same component on one page transfer and restore independently.
- Zero change to the wire format version, codec, scoped CSS attributes, or the fetch/resource payload sections.

**Non-Goals:**

- Cross-environment creation-order mismatches (environment-conditional trees) stay unsupported, consistent with DOM hydration adoption.
- `hydrate=False` does not change payload provisioning or window semantics: the SSR payload script is emitted for prerendered pages regardless of the browser-side `hydrate` flag, and the browser provides it whenever present; the window spans only the first render pass and closes at its end in all modes.

## Decisions

### 1. Close the payload at the hydration window boundary, not consume-once

Add `RenderContext._hydration_payload_closed: bool = False`. `AppDocumentRoot._render()` sets it to `True` immediately after the reveal-gating render-task drain (alongside the `_hydration_in_progress` reset), so the window closes as soon as the initial render pass completes; the method-level `finally` keeps assigning the flag as an idempotent error-path safety net (render exceptions, non-hydrate first renders). A small helper (`_is_hydration_payload_open()`) resolves the active render context via `_active_app_context.get() or _get_app_instance()` and returns the negated flag (default: open when no context exists, preserving unit-test behavior).

- `_try_resolve_payload_key()` (`signal/_composable.py`) returns `_MISSING` when closed.
- `use_async_result()` (`components/_hooks.py`) skips the `HYDRATION_DATA_KEY` restore when closed.

**Why over consume-once per entry:** consume-once breaks legitimate double creation during hydration (e.g., error-boundary resets, re-rendered subtrees) and still mis-pairs values for multi-instance pages. Window gating matches the spec's existing intent ("Factory runs on browser client-side navigation") and has exactly one state transition.

**Why close right after the drain:** the window deliberately includes the `await scheduler.await_pending(only_render=True)` drain so async component setups and Suspense resolutions that gate the reveal still restore; closing at that point matches the delta spec ("closes when the initial render pass (including the render-task drain that gates the hydration reveal) completes"). Anything after the drain — loading fade-out, wake wait, lazy-route preloading, early client-side navigation during boot — runs with the payload closed, so late component setups cannot restore stale values. The `finally` assignment remains as a safety net for failure paths and is idempotent on later re-renders.

**Verified by spike:** this gate alone fixes the docs_app demo bug (code block follows navigation; main-frame fetch resumes) while initial hydration still restores without a network round-trip; all 4955 unit tests pass.

### 2. Per-instance transfer id alongside, not replacing, `component_id`

`Context` gains `_transfer_id`; `ComponentProperty` gains `transfer_id`. Computed in `Component.__setup__` before the setup function runs:

```
app_ctx = _active_app_context.get() or _get_app_instance()
transfer_id = app_ctx._next_transfer_id(component_name) if app_ctx else generate_id(component_name)
```

`RenderContext._next_transfer_id(name)` increments a per-context `dict[str, int]` counter and returns `f"{generate_id(name)}#{n}"`.

- Collection (`hydration/_collect.py`) keys `signals` / `async_results` by `_property["transfer_id"]` (falling back to `component_id` for hand-built test doubles).
- Restoration (`_try_resolve_payload_key`, `use_async_result`) looks up `ctx._transfer_id`.
- `component_id` (scoped CSS, diagnostics) is unchanged.

**Why ordinals over random ids:** SSR collection and browser hydration must agree on keys without communication; per-name creation-order ordinals are deterministic on both sides because both build the same tree in pre-order (parents construct children during setup; route-level components are created at their `RouterView` position during the render pass in both environments).

**Why not DOM-anchored ids:** restoration must happen during setup (factory-skip design), before the component owns or adopts a DOM node, so DOM position cannot feed the key.

### 3. No changes to fetch cache or resource transfer

`BrowserFetchPort._response_cache` is keyed by URL (+method/body) and `RESOURCE_DATA_KEY` by path; neither collides across component instances, and both are intentionally app-lifetime caches. They keep working unchanged, which also preserves the no-refetch initial load observed in docs_app.

## Risks / Trade-offs

- **Creation-order drift between SSR and hydration** (e.g., async components resolving at different positions) → instances could restore a sibling's value. Mitigation: ordinals are assigned at construction (pre-order), and both environments construct the tree the same way; mismatched trees already fail DOM hydration adoption. Residual risk accepted and documented in the spec.
- **Testing-module / unit-test doubles** that never attach a `RenderContext` → they fall back to bare `generate_id(name)` keys, keeping existing tests and payload fixtures valid.
- **Suspense-resolved subtrees created after the reveal** (client-side async boundaries) → their `use_state()` runs after the window closes and will not restore; they render factory defaults as if client-navigated. Mitigation: SSR awaits Suspense content, and the browser drain covers render-scoped resolution (bounded by the element's `timeout`, mirroring the SSR-side `wait_for`); post-reveal resolution was already a client-side render.
- **`hydrate=False` apps may restore without DOM adoption** → when a prerendered page ships a payload, first-render setups can restore transferred values even though the `_hydrate_node` pass is skipped; this mirrors pre-existing behavior, and the window still closes at the end of the first render pass, so no stale-restore window remains.

## Addendum (round 2): AI review follow-ups

The CI AI review of PR #271 requested three must-fix items before merge. Design of the follow-up changes:

### A. Browser fallback must survive overlapping disposes

`RenderContext.__init__` (pyscript) overwrote the module-level `_app_instance` / `_app_di_scope` fallbacks, and `dispose()` cleared them unconditionally. With two overlapping browser contexts, disposing either one erased the surviving context's fallback, breaking callback-side injection. Each context now stores the previous fallback pair on creation; `dispose()` clears/restores only when it is still the current fallback, walking past already-disposed predecessors to re-select the last live context (no new module-level globals).

### B. Payload closure must use the same active-or-fallback context lookup

`AppDocumentRoot._render()` obtained `ctx` only via `_active_app_context.get()`, while `_is_hydration_payload_open()` also falls back to `_get_app_instance()`. A PyScript JS-originated render task without ContextVar propagation would never close the payload and would skip the reveal-gating render drain. `_render()` now resolves the context via `_active_app_context` → per-app `_render_context_cv` → `_app_instance` at hydration start, before the drain, and in the `finally`.

### C. Suspense must restore the pre-resolution DI scope

`provide()` during component setup switches `_active_di_scope` to the component child scope without a token. The identity-guarded `DIScope.__exit__` (introduced for dispose hygiene) silently no-ops when a descendant scope is active, leaking the child scope into Suspense siblings. A shared `_restore_suspense_di_scope(scope, original_scope)` helper (`_server_render`, `_browser_resolve`, `_hydrate_node`) exits the resolution scope and deterministically restores the pre-Suspense active scope.

## Addendum (round 3): second AI review follow-ups

The second CI AI review of PR #271 raised three must-fix and two should-improve items. Design of the follow-up changes:

### A. Dispose must unwind descendant DI scopes

`RenderContext.dispose()` only reset `_active_di_scope` when the *root* scope was the current value. Because `provide()` binds an untokenized component child scope, disposing while that child was active skipped the reset and then disposed the whole tree with the ContextVar still pointing at a disposed scope. `dispose()` now walks the active scope's parent chain and, when the binding belongs to the disposed tree (root or descendant), resets it to the pre-render value via the stored token (falling back to `set(None)` when the token does not belong to the current context). Active scopes of other live render contexts are left untouched.

### B. Non-hydrating apps must close the payload before loading teardown

The pre-fade closure in `AppDocumentRoot._render()` was guarded by `_app._hydrate`, so `hydrate=False` browser apps kept `_is_hydration_payload_open()` true through the loading fade and lazy-route preload, restoring stale initial-page values there. The closure (and `_hydration_in_progress` reset) now runs immediately after the initial child render for every browser mode; the render-task drain and mismatch summary remain hydrating-mode-only.

### C. Suspense hydration must snapshot the scope before probing

`_hydrate_node()` generated the probe children before capturing `original_scope`, so a probed `provide()` baked its leaked child scope into the snapshot; the fast path's identity-guarded `__exit__` then no-opped and the deferred path restored the leaked scope as its "original". The snapshot is now taken before probe generation, the fast path uses `_restore_suspense_di_scope`, and `_browser_resolve` accepts a pre-captured `original_scope` (also wired from `_browser_render`, with drift restoration added on the synchronous no-pairs path).

### D. Hydration fallback components must not consume transfer ordinals

Both the probe tree and the speculative hydration fallback advanced per-name ordinal counters, although SSR normally constructs only the resolved tree. Same-named components created after the boundary then diverged from SSR ordinals and missed transferred state. `RenderContext._next_transfer_id` now has a probe-depth mode returning provisional bare `generate_id(name)` ids without advancing counters; `_hydrate_node()` wraps fallback generation in that mode. The retained probe branch keeps its SSR-aligned consumed ordinals, and later components continue numbering from the SSR-aligned counter.

### E. Timed-out probe subtrees must be destroyed

The deferred-resolution timeout branch cancelled only the pending coroutines, leaking destroy hooks, effect scopes, and child DI scopes of synchronously-created probe components. The branch now runs the normal `_remove_element` teardown over the discarded probe subtree without touching the live fallback.

## Addendum (round 4): third AI review follow-ups

The third CI AI review of PR #271 raised three must-fix and two should-improve items that were regressions of the round-2/3 fixes.

### A. Deferred Suspense must restore the caller

`_browser_render()` and the deferred branch of `_hydrate_node()` captured `original_scope` and passed it to the scheduled `_browser_resolve()` task, but the resolver runs in a separate `AsyncScheduler` task, so its `finally` cannot repair the caller's `ContextVar`. If a probed child called `provide()`, the caller remained bound to that descendant, and the fallback was constructed under the leaked scope. The synchronous caller now restores `original_scope` immediately after probe generation and again after fallback construction, before scheduling.

### B. DIScope context manager must not leak descendants

`DIScope.__exit__` was changed to `if token is not None and get is self: reset`, so a `with scope:` block that contained a `provide()` (which `set()`s a child without a token) left the child active after the block. `__exit__` is restored to unconditional `reset(token)` with a `try/except` fallback to `set(None)`, preserving the normal context-manager contract. Overlapping-dispose safety remains in `RenderContext.dispose`, which already guards foreign active scopes via the `get is self` check before touching ContextVars.

### C. Probe teardown must be single-owner and cancellation-safe

The timeout branch called `_cleanup_pending_pairs()` and then `_remove_element()` on the same probe subtree, so pending components ran their destroy path twice (once via the pending-cleanup flag and once via the normal destroy path). Cancellation only cleaned pending pairs, leaking synchronously-created probe components. Both paths now use a single recursive `_remove_element` loop over `children`, without a separate `_cleanup_pending_pairs` call; the loop is reused for timeout, cancellation, and error replacement, and the live fallback is never touched.

### D. SSR timeout fallback must use provisional ordinals

`_server_render()` created timeout fallback components with normal consuming ordinals, while the hydration fallback path is explicitly provisional and non-consuming. For an SSR timeout, the fallback's transferable state was collected under an ordinal that the browser's provisional fallback did not use. `_server_render()` now wraps fallback generation in the same `_transfer_probe_depth` provisional guard as `_hydrate_node()`, so both sides use bare `generate_id(name)` for fallback and later same-named components stay aligned.

### E. Dispose must walk the full predecessor chain

`RenderContext.dispose` reset each of `_active_app_context`, `_render_context_cv`, and `_active_di_scope` via their token and then did `if cur is disposed: set(None)`, handling only one disposed predecessor. With three overlapping contexts, disposing the middle and then the newest lost the oldest live context. Each `RenderContext` now stores its predecessor values (`_prev_active_app_context`, `_prev_render_context_cv`, `_prev_active_di_scope`) at creation; dispose walks the chain past disposed entries to the next live context (or `None`) and restores that instead of clearing. The module-level fallback already walked; the ContextVar paths now do the same.
