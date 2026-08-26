## 1. Classifier and dual-run sweep

- [x] 1.1 Add `webcompy_cli/_browser_probes.py` AST classifier (separate file from archived Phase1 `_browser_test_harness.py`,案A; reuses `BROWSER_TEST_DIR` via import, no Starlette/uvicorn dep): walks `tests/**/*.py`, flags top-level `js`/`pyscript`/`pyodide`/`webcompy_testing` fake imports and module-scope side-effecting calls as ineligible, allows function-local `js` imports to remain eligible, respects `# browser-dualrun: eligible` / `# browser-dualrun: skip` pragma, and emits `eligible.txt` and `ineligible.json` sorted repo-relative. Public functions SHALL carry Google-style docstrings per `api-docstrings`.
- [x] 1.2 Implement driver-side dual-run sweep: CPython `pytest tests/` over `eligible.txt` → `{test_id: outcome}` map, PyScript harness load of same modules via existing `[files]` mount + `run_one(test_id)` sequential session → same-shaped map, bucket into `both-pass`/`CPython-only-fail`/`PyScript-only-fail`/`both-fail`, write `artifacts/browser-dualrun.json`, and print a terminal summary table.

## 2. In-page runner dual-run extension

- [x] 2.1 Extend the Phase 1 in-page runner/harness to discover and import dual-run modules from the mounted `tests/` mirror, reusing the per-test isolation (fresh `WebComPyApp`/`BrowserRenderContext`, `dom_root` teardown, stdout/stderr + console-error + traceback JSON) and repo-relative traceback rewriting.
- [x] 2.2 Wire harness entry points `scripts/run-browser-tests.sh --dual` and `WEBCOMPY_RUN_DUAL=1` / `WEBCOMPY_RUN_BROWSER=1` gating for the dual-run sweep; default to informational (no hard CI gate on divergence) with an extensible bucket-promotion hook for later triage.

## 3. Probe suite (tests/browser/probes/)

- [x] 3.1 Add `tests/browser/probes/` as the authoritative probe battery (ordinary browser-tier tests, grouped as the `probes` suite in reports, hard gate on failure): initial probes covering `asyncio.sleep(0)`/WebLoop ordering, `create_proxy`/`destroy` lifecycle (including idempotent destroy and survival across awaits), `js` `to_js`/`is_none`/`undefined` interop, and `Text.splitText` UTF-16 boundaries (including surrogate-half behavior matching `FakeDOMNode.splitText`'s spec).
- [x] 3.2 Provide probe authoring convention: module docstring is the contract statement; any new `tests/browser/probes/test_probe_*.py` is auto-discovered by the harness manifest without code changes; `scripts/run-browser-tests.sh --probes` runs only `tests/browser/probes/**` via the harness.

## 4. Version-bump sweep

- [x] 4.1 Implement version-bump sweep orchestration: with `WEBCOMPY_PYSCRIPT_CANDIDATE=<version>` (populated from `workflow_dispatch` `pyscript_candidate_version`), re-download `runtime-assets/{candidate}/` via the existing runtime downloader, execute probes (and, when requested, the dual-run tier) at the pinned and candidate versions in the same harness code, diff probes into `{only_pinned_pass, only_candidate_pass, both_pass, both_fail}` (and dual-run buckets likewise), and write `artifacts/browser-version-sweep.json`; fail the CI job when any `probes` probe regresses.

## 5. inspect pyexec (inspect-pyexec, independent from inspect-cli,案B)

- [x] 5.1 Add `webcompy inspect pyexec` single-shot subcommand (new `inspect-pyexec` capability, CLI remains `inspect` for discoverability but spec is independent; implementation lives with harness `webcompy_cli/_browser_test_harness.py` + `webcompy_testing/browser_runner/`): launches a single harness session (same boot path as Phase 1, `experimental_create_proxy: "auto"`, local `interpreter`/`lockFileURL`), calls a harness `evaluate(code)` sibling of `run_one` (proxied via `create_proxy`, awaited via `page.evaluate`), captures `stdout`/`stderr`/`result_repr`/console-error delta, and prints JSON `{"stdout","stderr","result_repr","console_error_delta","exc_type","traceback"}`; support `--file <path>`. Public functions SHALL carry Google-style docstrings (no OpenSpec references) per `api-docstrings` strict coverage.
- [x] 5.2 Add `webcompy inspect pyexec --repl`: keeps the same harness session/Playwright page alive, loops `stdin line → evaluate → JSON line` preserving interpreter state across turns, with `--repl-timeout` (default 300s) and SIGINT/Ctrl-D teardown of browser + harness server. Public functions SHALL carry Google-style docstrings per `api-docstrings`.

## 6. Docs, CI, and housekeeping

- [ ] 6.1 Update `AGENTS.md` File → Spec Mapping, Framework Invariants, and Current Specs list for `browser-dualrun`, `browser-probes`, and `inspect-pyexec`; update `.opencode/skills/webcompy-review/SKILL.md` to keep the mapping and invariants in sync; run `python3 scripts/check-doc-spec-refs.py` and confirm it passes.
- [ ] 6.2 Extend the `browser-tests` CI job (Phase 1) with `dual` and `probes` modes; add a manually-triggered `browser-version-sweep` workflow (`workflow_dispatch` `pyscript_candidate_version` → `WEBCOMPY_PYSCRIPT_CANDIDATE`).
- [ ] 6.3 Record the classifier's initial `eligible.txt`/`ineligible.json` output (reviewed) and document the probe/`PYSCRIPT_VERSION` bump procedure in `CONTRIBUTING.md` (and, if it describes test layout, the dual-run eligibility and pragma convention).
