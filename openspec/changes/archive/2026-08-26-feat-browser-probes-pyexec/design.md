## Context

After Phase 1 (`feat-browser-test-harness`), the repository has a PyScript-native harness: a Starlette server exposing `/_webcompy-assets/*` from `runtime-assets/{PYSCRIPT_VERSION}/`, `/testharness` with a single `<script type="py">` boot and `window.__webcompy_test__.run_one(test_id)` proxied entrypoint, and a pytest integration that collects `tests/browser/**` (CPython-importable, `js` imports function-local) and dispatches each `test_id` to the page returning JSON. Phase 2 reuses that session-scoped interpreter to do three things the harness does not yet cover: run a subset of the existing `tests/` suite inside PyScript and diff it with the CPython run, run a small probe battery that codifies PyScript-only contracts, and provide an ad-hoc `pyexec` loop. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- A repeatable classifier that partitions `tests/` into eligible / browser-only / CPython-only without editing test bodies.
- A harness extension that loads eligible `tests/` modules from the Emscripten FS (same `[files]` mount as Phase 1) and reuses the in-page runner's `run_one` path so the same function executes in both interpreters.
- A first-class diff report (JSON + pytest outcome) bucketed `both-pass` / `CPython-only-fail` / `PyScript-only-fail` / `both-fail`.
- A `tests/browser/probes/` battery whose failures are authoritative for PyScript-version bumps (sweep workflow runs the same battery at the pinned and candidate `PYSCRIPT_VERSION` and reports the delta).
- A single-shot and REPL-friendly `webcompy inspect pyexec` that executes code inside a real PyScript interpreter via the same harness session machinery.

**Non-Goals:**
- Stable downstream-app testing API guarantees; Phase 2 remains framework-internal.
- Editing or auto-fixing ineligible `tests/` bodies to make them dual-run eligible.
- Running full pytest inside Pyodide as the dual-run engine (kept as a documented spike).
- `pyexec` evaluating code on the production server process (it targets the harness interpreter).

## Decisions

### D1 — Superset classifier is a read-only AST pass over `tests/`, not a runtime import (separate file,案A)

An `ASTClassifier` in `webcompy_cli/_browser_probes.py` (separate from the archived Phase1 `webcompy_cli/_browser_test_harness.py`; 453 lines) walks `tests/**` and tags a module as ineligible if its top-level contains:

- any import whose module name is `js`, `pyscript`, `pyodide`, `webcompy_testing` fake ports, or `e2e.*`;
- any top-level `pytest.skip`/`xfail` conditioned on `sys.platform`;
- any top-level I/O or network side effects detected via a conservative allowlist (`import`/`def`/`class`/`Assign` of constants are eligible; `Call` at module scope is not).

`ast.Import`/`ast.ImportFrom` inspection is cheap and has no Emscripten involvement. Modules that import `js`-family symbols *inside* functions are still eligible (those imports are only evaluated in-page). The classifier emits `eligible.txt` / `ineligible.json` (with reason per file) and is wired as a build-time step of the dual-run sweep; CPython collection simply reads `eligible.txt` for the runner's inventory. CPython's own `pytest tests/` discovery runs unchanged. The classifier reuses `BROWSER_TEST_DIR` from `webcompy_cli._browser_test_harness` to avoid duplicating the discovery constant, but otherwise has no Starlette/uvicorn/pyodide dependency so it remains importable in lightweight lint contexts (unlike the harness server). This is distinct from `scripts/check-browser-imports.py`, which guards `tests/browser/**` importability; the classifier guards `tests/` dual-run eligibility.

*Alternative considered:* runtime collection by importing each `tests/` module in a PyScript session and catching `ImportError`. Rejected — it makes the classifier's feedback loop require a full PyScript boot and pollutes `sys.modules`.

*Alternative considered (placement):* integrating the classifier into `_browser_test_harness.py`. Rejected — that file is Phase1-archived and already 453 lines; separate file preserves cohesion, keeps the harness stable (no `browser-test-harness` delta needed), and keeps the classifier importable without heavy dependencies.

### D2 — Dual-run is a two-sided sweep orchestrated from the CPython pytest driver, not inside the harness alone

1. CPython side: `WEBCOMPY_RUN_DUAL=1` (implicitly set by `scripts/run-browser-tests.sh --dual` / `run-browser-probes.sh`) runs `pytest tests/` over `eligible.txt` and records a JSON map `{"test_id": "passed"|"failed"|"skipped"}` (and `pytest` exit code/traceback path).
2. PyScript side: the harness session loads those same eligible modules from the already-mounted `tests/` mirror, resets the in-page fixture/DI/ DOM between tests as in Phase 1, calls the existing `run_one(test_id)` for each id, and streams the same-shaped JSON map back via `page.evaluate`.
3. The driver post-processes into the bucketed diff + writes `artifacts/browser-dualrun.json` (and prints a summary table in the pytest terminal summary hook). No code change in `tests/` files is needed; the imports happen from the harness `[files]` mount so repo-relative traceback rewriting already exists from Phase 1.

*Alternative considered:* load `tests/` modules only inside PyScript and skip the CPython counterpart. Rejected — without the counterpart, divergence has no reference.

### D3 — Probe battery is a normal `tests/browser/probes/` directory, not a new framework

Probes are ordinary browser-tier test modules matching `tests/browser/probes/test_probe_*.py` using the same `app`/`dom_root` fixtures as Phase 1. Each probe codifies one contract (e.g., `test_probe_webloop_ordering.py`: `asyncio.sleep(0)` and scheduler microtask ordering; `test_probe_utf16_dom.py`: `splitText` and surrogate-boundary contracts). The "probe" designation is only a reporting concern: the driver groups `tests/browser/probes/**` results under a `probes` suite in the report and treats any probe failure as a hard failure.

*Alternative considered:* a custom DSL for probes (YAML specs → driver-generated tests). Rejected — reusing the browser-tier collection keeps the authoring surface identical and avoids a second runner.

### D4 — Version-bump sweep is a single harness-session diff across two PyScript versions

The sweep workflow (`browser-version-sweep`, manual or `workflow_dispatch`) runs the probe (and optionally dual-run) suite twice, re-downloading `runtime-assets/{candidate_version}/` via the existing `webcompy_cli/_runtime_downloader` path (`PYSCRIPT_VERSION` overridden by `WEBCOMPY_PYSCRIPT_CANDIDATE=<version>` for that run). Both runs execute on the same harness code; the delta is `candidate_t vs pinned_t` for each probe/dual-run id. The artifact is `artifacts/browser-version-sweep.json`; the CI job fails if any `probes` probe regresses.

Candidate version assets are never promoted automatically — the sweep is informational.

### D5 — `inspect pyexec` reuses the harness session, not a new codepath (independent `inspect-pyexec` capability)

`webcompy inspect pyexec "<code>"` (and `webcompy inspect pyexec --file path.py`) starts a single-harness session (same boot path as Phase 1, same `interpreter`/`lockFileURL`), calls a new `window.__webcompy_test__.evaluate(code: str)` entrypoint (a sibling of `run_one`, proxied the same way) that runs `pyodide.runPythonAsync`-style evaluation through the in-page runner's captured `stdout`/`stderr` and console-error delta, and returns `{"stdout","stderr","result_repr","console_error_delta"}` as JSON. With `--repl`, the command keeps the harness session alive and loops `read → evaluate → print` (stdin is CPython-side `input()`, evaluation is always driver→`page.evaluate`). The CLI remains `webcompy inspect pyexec` for discoverability, but the spec is an independent `inspect-pyexec` capability (not a delta on `inspect-cli`): its runtime model (harness-backed, REPL lifetime) is distinct from `inspect-cli`'s `webcompy start` server model (`PID file`/`SIGTERM`/independent browser per command). Implementation lives alongside the harness (`webcompy_cli/_browser_test_harness.py` + `webcompy_testing/browser_runner/`) rather than `webcompy_cli/_inspect.py`, so File→Spec mapping stays 1:1.

No separate `pyexec` daemon or app-server route is needed; the harness lifetime is the `pyexec` invocation's session. Security: evaluation is confined to the harness interpreter, not the production server's process.

*Alternative considered:* exposing `pyexec` as `/_webcompy-eval` on the production `webcompy start` server. Rejected — it would require auth/lifecycle controls and creep beyond the harness scope.

*Alternative considered (spec placement):* keeping `pyexec` as a MODIFIED delta on `inspect-cli`. Rejected — it mixes two runtime models in one spec and splits implementation across two files for one spec, weakening cohesion and future evolution.

## Risks / Trade-offs

- **Classifier false positives (eligible marked ineligible)** → Mitigation: keep the AST rule set conservative and emit `ineligible.json` with a per-file reason; an operator can waive a file by adding a `# browser-dualrun: eligible` pragma in a trailing comment and the classifier respects it.
- **Classifier false negatives (non-eligible imported in PyScript, fails noisy)** → Mitigation: failures are not a CI hard gate for dual-run (see next risk); the individual test's traceback explains the `ImportError` and the file can be moved to `ineligible` by adding the pragma `# browser-dualrun: skip`.
- **Dual-run diff is noisy (pre-existing CPython fakes distort expectations)** → Mitigation: the dual-run suite is informational by default (no hard gate on divergence). Only the probe suite (curated, small) is authoritative. Over time, dual-run `PyScript-only-fail` buckets that are true bugs are fixed and become non-divergent; buckets that reflect intentional CPython-fake divergence are tagged via the module pragma or `pytest.mark.browser_only`.
- **Phase-2 sweep needs two full PyScript boots (pinned + candidate)** → Mitigation: the sweep workflow is opt-in (`workflow_dispatch` + `WEBCOMPY_PYSCRIPT_CANDIDATE` input), not on every PR. Per-PR, the probes+dualrun run only against the pinned version.
- **`pyexec` long-lived REPL keeps a Chromium session alive (resource leak risk)** → Mitigation: session-scoped Chromium with an idle timeout (`--repl-timeout 300`) that tears down the harness; `Ctrl-D` also exits cleanly; SIGINT handler tears down both the browser and the harness server.

## Migration Plan

1. Land behind `WEBCOMPY_RUN_BROWSER=1` extensions (no default discovery change). `scripts/run-browser-tests.sh` gains `--dual`/`--probes` flags forwarding to the same env-var-gated pytest extensions; a new `scripts/run-browser-probes.sh` wrapper may alias them.
2. Ship the AST classifier and the `eligible.txt` generator; commit its initial output (reviewed) so CI can run the harness dual-run sweep without recomputing.
3. Add the `tests/browser/probes/` battery (3–5 probes in the first cut).
4. Wire a `browser-tests` extension job (informational first, promotable) and the manual `browser-version-sweep` workflow that consumes `WEBCOMPY_PYSCRIPT_CANDIDATE`.
5. Wire `inspect pyexec` as a thin wrapper over the harness session; no harness-server lifecycle change beyond the extra entrypoint.

No rollback complexity beyond dropping the new scripts and unsetting the env var.

## Open Questions

- None that block specs/tasks. The exact probe list for the first cut (the 3–5 initial probes) is a task-level calibration; broadening it is incremental and does not change the sweep or harness contracts.
