# Design: Improve Startup Performance

## Context

Startup measurement on docs_app (`.tmp/measure/report.md`) established: interaction time is dominated by PyScript/Pyodide runtime download + initialization (~12.8 MB transferred, ~2–3 s wall); custom-element registration/binding is <50 ms; navigation is fast (60–110 ms). A regression blocks further measurement: `profile=True` crashes browser startup because the generated bootstrap (`webcompy_server/_html.py`) writes `app._profile_data["pyscript_ready"]`, but `WebComPyApp` does not expose `_profile_data` (the dict lives on `RenderContext`). See proposal.md for motivation.

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

Move profile data ownership to the app instance: `WebComPyApp.__init__` creates `self._profile_data: dict[str, float] = {}` when `self._profile` is True, and `_record_phase`/`_emit_profile_summary` operate on it directly. The `RenderContext._profile_data` attribute and its `ctx._record_phase` indirection are removed; `app.profile_data` returns `self._profile_data`.

Rationale: the generated HTML writes `app._profile_data["pyscript_ready"]` *before* any `RenderContext` exists (`app.run()` creates it afterwards), so the data cannot live on the context. The `app-lifecycle` spec already requires `WebComPyApp._record_phase` and `_emit_profile_summary` to record into `_profile_data`, so this aligns the implementation with requirements.

Alternatives considered:
- Make `_app.py` create the context first and record later — contradicts bootstrap ordering (timestamp captured before `app.run()`).
- Change the generated HTML to call a setter (`app._set_pyscript_ready(...)`) — noisier than giving the app the dict its spec already promises.

### D2: Phase recording lives behind `_profile` guard

`WebComPyApp._record_phase` SHALL no-op when `self._profile` is False, preserving zero-overhead in default runs. `WebComPyApp.__init__` SHALL create `_profile_data` only when profiling is enabled.

### D3: Two new phases in the summary

- `var custom_elements_defined`: recorded around `AppDocumentRoot._ensure_custom_elements_defined()` (bulk `customElements.define` pass before hydration).
- `var lazy_preloaded`: recorded around `Router.preload_lazy_routes()` batch execution (the scheduled macro task that resolves lazy route generators).

The summary pairs extend `_emit_profile_summary` with `run_done → custom_elements_defined` and `custom_elements_defined → lazy_preloaded` (or analogous adjacency once actual call order is confirmed during implementation). `_root_component` and `_router` record via `app._record_phase` so the app instance is the single owner.

Rationale: these were the two measured cost clusters; making them first-class phases lets future startup work compare against the profile output without probe hacks.

### D4: Delivery improvement deferred to follow-up

Do not modify `pyscript-bundle` or CLI delivery behavior in this change. The measurement shows runtime download dominates, but choosing delivery mode (wasm/runtime serving, standalone, cache headers) is a deployment decision with trade-offs; a follow-up change owns it and re-uses the restored profiler for validation.

## Risks / Trade-offs

- [Removing `RenderContext._profile_data` may break server-side tests that read `ctx.profile_data`] → Keep `app.profile_data` as the public accessor; update `tests/test_profiling.py` to exercise app-owned data; run unit tests to confirm server paths (SSG/dev server) still emit summaries via `print()`.
- [New phases change profile output format, breaking consumers] → The summary is diagnostic (console), not an API; still update the archived-format doc example in specs/docs to match.
- [Double call sites for `preload_lazy_routes` (view + root) may double-record] → Use one-time flags keyed by phase name so a phase records its earliest/first occurrence (`_record_phase` sets a key once).

## Migration Plan

- This change alters only diagnostic behavior; no deployment migration.
- Rollback: the `_profile_data` ownership change and new phases are isolated to `_app.py`, `_root_component.py`, `_router.py`, `_render_context.py`, and tests; reverting restores prior profiling behavior.

## Open Questions

- Whether `lazy_preloaded` should time the synchronous `_preload()` of each component or the whole scheduled batch — resolved during implementation from the scheduling API (the summary can show either; pick the batch wall time for comparability with the measurement report).
- Whether to also record the per-`.whl`/`.wasm` resource timings in the summary (browser Performance API) — deferred; external measurement already covers it.