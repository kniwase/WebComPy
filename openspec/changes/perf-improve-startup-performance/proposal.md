# Proposal: Improve Startup Performance

## Why

Startup measurement on the docs_app (see `.tmp/measure/report.md`) shows the interaction time is dominated by PyScript/Pyodide runtime download and initialization (~12.8 MB transferred, ~2–3 s wall), while custom-element registration and FFI binding total under 50 ms. Separately, the measurement surfaced a regression: enabling `WebComPyAppConfig(profile=True)` crashes browser startup with `AttributeError` because the generated bootstrap references `app._profile_data`, which `WebComPyApp` does not provide. We cannot improve what we cannot measure, so this change restores the profiling infrastructure and targets the actual dominant startup cost.

## What Changes

- Fix the `profile=True` browser startup crash: `WebComPyApp` SHALL own a `_profile_data` dict so the generated `<script type="py">` bootstrap can record the `pyscript_ready` timestamp, restoring the `[WebComPy Profile]` console summary.
- Align the `app-lifecycle` and `cli` specs with the config-based profile API (`WebComPyAppConfig(profile=True)`, not `WebComPyApp(profile=True)`) and with where `_profile_data` lives.
- Extend the profile summary with custom-element registration and lazy-preload phases so future startup work can attribute cost without probe hacks.
- Investigate the dominant runtime download/initialization cost (delivery of `pyodide` runtime assets, wheel serving, caching) and record the findings as the basis for a follow-up change; do not modify serving behavior here.
- Confirm custom-element registration is NOT a target: document that the measured cost is <50 ms and de-prioritize any registration/binding optimization.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `app-lifecycle`: Profile data ownership is corrected so `WebComPyApp` SHALL own a `_profile_data` dict (per the existing requirement's method contract), fixing the `profile=True` browser crash; the profiling summary gains two added phases (custom-element bulk-registration and lazy-preload); and the profiling scenario is aligned to the config-based profile API (`WebComPyAppConfig(profile=True)`).

## Impact

- `packages/webcompy/src/webcompy/app/_app.py` — add `_profile_data`, adjust phase recording/summary.
- `packages/webcompy/src/webcompy/app/_root_component.py` — record custom-element bulk-registration phase around `_ensure_custom_elements_defined`.
- `packages/webcompy/src/webcompy/router/_router.py` — record lazy-preload phase in `preload_lazy_routes`.
- `packages/webcompy-server/src/webcompy_server/_html.py` — unchanged bootstrap contract (already emits `app._profile_data[...]`); may need CORS/cache handling if delivery changes.
- `packages/webcompy-cli/` — runtime asset delivery options **if** the measured improvement requires serving/caching changes (investigated; a follow-up change may modify `pyscript-bundle` delivery requirements).
- Tests: `tests/test_profiling.py` (extend for new phases/`_profile_data` ownership), `tests/test_cli_*.py` (bootstrap inspection), unit + docs E2E.
- Docs: `docs_app/documents/` profiling guidance updates.

## Known Issues Addressed

- Regression discovered during startup measurement: `profile=True` crashes browser startup because the generated HTML references `app._profile_data`, which does not exist on `WebComPyApp` (design divergence in the archived `feat-hydration-measurement` change).

## Non-goals

- Custom-element registration optimization (案②/③/④ from the measurement discussion): measured cost is <50 ms; spec changes there are not justified.
- General re-rendering/VDOM diffing performance work uncovered by this measurement.
- Publishing packages to PyPI (handled elsewhere per known issues).
- Broad changes to the UI theme/stylesheet delivery pipeline not related to startup transfer.