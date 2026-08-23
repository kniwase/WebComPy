# Design: Improve Startup Performance

## Context

Startup measurement on docs_app (`.tmp/measure/report.md`, gitignored) established: interaction time is dominated by PyScript/Pyodide runtime download + initialization (~12.8 MB transferred, ~2–3 s wall); custom-element registration/binding is <50 ms; navigation is fast (60–110 ms). A regression blocks further measurement: `profile=True` crashes browser startup because the generated bootstrap (`webcompy_server/_html.py`) writes `app._profile_data["pyscript_ready"]`, but `WebComPyApp` does not expose `_profile_data` (the dict lives on `RenderContext`). See proposal.md for motivation.

Additional facts established during implementation planning:

- In the current implementation `run_start` is never actually recorded: `app.run()` calls `_record_phase("run_start")` before any `RenderContext` exists, and the app→ctx delegation silently no-ops. Moving ownership to the app makes this timestamp real — which also means the legacy summary pair `init_done → run_start` would display a negative value (chronologically `run_start` precedes ctx init), so the pair list must be restructured.
- The loading screen redesign (#259, `loading-screen` spec) fades out the loading element over `fade_out_ms` (default 250 ms) via `await asyncio.sleep(...)` before removing it. This await yields to the JS event loop, so view-scheduled lazy-preload batches (`setTimeout(0)`) typically fire during the fade — i.e. **before** `loading_removed` is recorded. Verified on docs_app: the batch can even complete before `run_done` (it fires during children-render awaits). Consequently neither `loading_removed` nor `run_done` works as an anchor for the lazy-preload stage; the summary therefore pairs a dedicated start marker with the completion timestamp instead (see D3).
- Interplay with `loading-screen/spec.md`: that spec does not mention profiling output; emitting the profile summary slightly later (macro task after removal) still satisfies the app-lifecycle requirement "printed to the browser console after the loading indicator is removed".

## Goals / Non-Goals

**Goals:**
- Restore the profiling feature in the browser: `profile=True` starts without crashing and emits the phase summary.
- Make startup cost attributable: add the custom-element bulk-registration phase and the lazy-preload phase to the profile summary and to `tests/test_profiling.py`.
- Keep the profiling contract consistent with generated HTML (the `<script type="py">` bootstrap already emits `app._profile_data[...]`).
- Document the measurement conclusion (custom elements are not a startup bottleneck) in the docs so future work does not target them.

**Non-Goals:**
- Delivering an actual runtime-download speedup in this change. The runtime-transfer improvement is investigated and queued as a separate change (delivery/caching options), because the fix depends on deployment trade-offs (CDN vs local, standalone, caching) that need their own design.
- Any custom-element registration/binding optimization (measured <50 ms).
- Deeper VDOM/re-render performance work.

## Decisions

### D1: `WebComPyApp` SHALL own `_profile_data`

Move profile data ownership to the app instance: `WebComPyApp.__init__` creates `self._profile_data: dict[str, float] = {}` unconditionally, and `_record_phase`/`_emit_profile_summary` operate on it directly. The `RenderContext._profile_data` attribute and its `ctx._record_phase` indirection are removed; `app.profile_data` returns `self._profile_data` when profiling is enabled, else `None`.

Rationale: the generated HTML writes `app._profile_data["pyscript_ready"]` *before* any `RenderContext` exists (`app.run()` creates it afterwards), so the data cannot live on the context. The `app-lifecycle` spec already requires `WebComPyApp._record_phase` and `_emit_profile_summary` to record into `_profile_data`, so this aligns the implementation with requirements. Creating the empty dict unconditionally (rather than only when profiling is enabled) is defensive and trivially cheap: stray direct assignments like the generated bootstrap line can never raise `AttributeError`.

Alternatives considered:
- Make `_app.py` create the context first and record later — contradicts bootstrap ordering (timestamp captured before `app.run()`).
- Change the generated HTML to call a setter (`app._set_pyscript_ready(...)`) — noisier than giving the app the dict its spec already promises.
- Create `_profile_data` only when `_profile` is True — saves one empty-dict allocation but makes every ungated access a potential `AttributeError`; rejected.

### D2: Phase recording lives behind `_profile` guard

`WebComPyApp._record_phase` SHALL no-op when `self._profile` is False, preserving zero-overhead in default runs. It SHALL also keep only the **first occurrence** of each phase name (`name not in self._profile_data`) — required by the at-most-once scenario in the delta spec, and it makes double scheduling of the lazy-preload batch harmless. Server-side consequence of app-owned data plus first-occurrence-wins: on SSR/SSG processes the recorded timestamps reflect the **first request handled per process**; subsequent requests record nothing new and `app.profile_data` keeps returning that first-request snapshot. Per-request init-phase timing visibility is therefore lost on the server — accepted, since server paths never emit summaries anyway.

### D3: New phases in the summary

- `custom_elements_defined`: recorded right after `AppDocumentRoot._ensure_custom_elements_defined()` completes (bulk `customElements.define` pass before hydration).
- `lazy_preload_start`: recorded in `Router.preload_lazy_routes()` when lazy components were found, right before scheduling the batch (browser) or starting the synchronous loop (server). First occurrence wins, so it captures the earliest preload attempt.
- `lazy_preloaded`: recorded when that preload batch finishes executing — inside `_batch_preload` in the browser (the scheduled macro task), and after the synchronous preload loop on the server. Recording happens via `inject(_APP_KEY, default=None)`; this is safe because the browser DI scope stays entered for the app lifetime and the server call runs inside the render scope.

**Why the lazy stage pairs start→end instead of anchoring on a lifecycle phase**: verified empirically on docs_app — the view-scheduled batch fires during the children-render awaits, so `lazy_preloaded` typically lands *before* both `run_done` and (sometimes) even before `custom_elements_defined`; any lifecycle-phase anchor would produce negative deltas. Pairing `lazy_preload_start → lazy_preloaded` yields the actual preload span (queue + execution), matching the external measurement (~40–45 ms).

**Summary emission is deferred in the browser**: `_root_component` replaces its synchronous `app._emit_profile_summary()` call with `schedule_macro_task(app._emit_profile_summary)`. Because `schedule_macro_task` uses `window.setTimeout(0)` (FIFO timer queue), every lazy-preload batch scheduled before the emit task runs before it, so the printed summary always reflects `lazy_preloaded` when any batch exists. This also keeps exactly one emission site (double scheduling of batches by `RouterView._on_set_parent` and `_root_component` cannot double-print).

**Pair list**: `pyscript_ready → imports_done`, `imports_done → init_done`, `init_done → custom_elements_defined`, `custom_elements_defined → run_done`, `run_done → loading_removed`, `lazy_preload_start → lazy_preloaded`. The legacy pairs `init_done → run_start` / `run_start → run_done` are dropped: with app-owned data `run_start` becomes real but chronologically precedes ctx init, so `init_done → run_start` would go negative; instead the whole first-render span shows up as `init_done → custom_elements_defined → run_done`. Finally, `_emit_profile_summary` SHALL skip a pair whose end timestamp precedes its start timestamp (defensive guard for out-of-order diagnostics). Note that `run_done → loading_removed` now includes the intentional fade duration from the loading-screen redesign — that is expected and documented here rather than "fixed".

### D4: Delivery improvement deferred to follow-up

Do not modify `pyscript-bundle` or CLI delivery behavior in this change. The measurement shows runtime download dominates, but choosing delivery mode (wasm/runtime serving, standalone, cache headers) is a deployment decision with trade-offs; a follow-up change owns it and re-uses the restored profiler for validation.

## Risks / Trade-offs

- [Removing `RenderContext._profile_data` may break server-side tests that read `ctx.profile_data`] → Keep `app.profile_data` as the public accessor; update `tests/test_profiling.py` to exercise app-owned data; run unit tests to confirm server paths (SSG/dev server) still work. Note that SSR/SSG runs never emit summaries — the only emission site is browser-gated (`_root_component`, pyscript env) and pre-existing; the `print()` branch of `_emit_profile_summary` is exercised by unit tests only.
- [New phases change profile output format, breaking consumers] → The summary is diagnostic (console), not an API; the delta spec pins the new pair list.
- [Double call sites for `preload_lazy_routes` (view + root) may double-record or double-print] → `_record_phase` keeps only the first occurrence per phase name, and there is exactly one emission site (root's deferred macro task), so both are structurally prevented.
- [`asyncio.sleep` yields let JS timers run mid-render] → This is exactly why emission is deferred via the FIFO timer queue rather than emitted inline at loading removal.

## Migration Plan

- This change alters only diagnostic behavior; no deployment migration.
- Rollback: the `_profile_data` ownership change and new phases are isolated to `_app.py`, `_root_component.py`, `_router.py`, `_render_context.py`, and tests; reverting restores prior profiling behavior.

## Open Questions

- ~~Whether `lazy_preloaded` should time the synchronous `_preload()` of each component or the whole scheduled batch~~ — Resolved: batch wall time, recorded at batch completion (D3).
- Whether to also record the per-`.whl`/`.wasm` resource timings in the summary (browser Performance API) — deferred; external measurement already covers it.

## Measurement Conclusions

Findings from the docs_app startup measurement that motivated this change (primary data: `.tmp/measure/report.md` and sibling JSON in `.tmp/measure/`, which are gitignored and referenced here only):

- **Custom-element registration is NOT a startup bottleneck.** The bulk `customElements.define` pass, per-component `ensure_defined`, FFI binding, and lazy-route preload all measure well under 50 ms combined on both dev and static serving. Any future optimization of registration/binding is de-prioritized.
- **The dominant startup cost is PyScript/Pyodide runtime transfer and initialization**: roughly 12.8 MB transferred (`pyodide.asm.wasm` ~8.6 MB, `python_stdlib.zip` ~2.4 MB, JS glue ~1.3 MB, app wheel ~393 KB) and ~2–3 s wall clock cold / ~2–2.35 s warm.
- Future startup work should therefore target **runtime delivery and initialization**, not component machinery.

## Runtime Delivery Options (follow-up basis)

Per D4 no delivery behavior changes in this change; the options below are recorded as candidates for a dedicated follow-up change:

- **`runtime_serving="local"`** (serve Pyodide from `_webcompy-assets/pyodide/`): removes CDN dependency and makes caching deterministic, but ships ~12 MB per deployment and requires the CLI asset pipeline.
- **CDN (default)**: zero deploy cost, but subject to third-party cache policy and network variability; cache headers cannot be controlled by the app author.
- **Cache headers for local assets**: when serving locally through the CLI/server, long-lived immutable cache headers on `.wasm`/`.zip` would make warm boots near-instant for repeat visitors. Low risk, but changes HTTP behavior → belongs to a follow-up change.
- **`standalone` builds**: inlines everything for offline use; largest transfer, only appropriate for specific deployment targets.
- **Wheel splitting / dependency trimming**: reduces the app-package portion (~393 KB), which is small relative to the runtime — low expected payoff.

Any material improvement selected from these options becomes its own change and reuses the profiler restored by this change for before/after validation.