# Tasks

## 1. Split DOM Text Coalescing and Unit Tests

- [ ] 1.1 Add `_collect_consecutive_text_nodes` and `_coalesce_text_nodes` helpers in `packages/webcompy/src/webcompy/elements/types/_base.py`, preserving `__webcompy_prerendered_node__` whenever any node in the coalesced DOM `#text` slice carried that flag; verify type safety with `uv run pyright`.
- [ ] 1.2 Update `_normalize_text_run` and `_normalize_hydration_text_runs` in `packages/webcompy/src/webcompy/elements/types/_base.py` so both single non-empty `TextElement` children and multi-`TextElement` runs coalesce `k >= 2` consecutive DOM `#text` nodes whose concatenated text matches the expected text while keeping `_text_run_matches_dom` fast-path and mismatch reporting intact; verify with `uv run python -m pytest tests/test_hydration_text_merge.py -v --tb=short`.
- [ ] 1.3 Add unit tests in `tests/test_hydration_text_merge.py` (`TestHydrationSplitTextCoalescing`) covering single-element split `#text` coalescing, trailing prerendered flag preservation, mismatched split runs, multi-element coalescing with `splitText` alignment, aligned fast-path preservation with stray trailing `#text`, and sibling element `_node_idx` alignment; verify all tests pass with `uv run python -m pytest tests/test_hydration_text_merge.py tests/test_hydration_report.py tests/test_full_hydration.py --tb=short`.

## 2. CI Checks and Real-Browser Verification

- [ ] 2.1 Verify static analysis, docstrings, browser import invariants, spec references, and unit test suite pass (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pydoclint ...`, `uv run python scripts/check-browser-imports.py`, `python3 scripts/check-docstrings.py`, `python3 scripts/check-doc-spec-refs.py`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short`), and confirm `openspec/SPEC_INDEX.md` and `.agents/skills/webcompy-review/SKILL.md` remain aligned with `elements/spec.md`.
- [ ] 2.2 Verify `/sample/ui-form-controls/` and hydration preservation in a real Chromium/PyScript runtime (`scripts/run-e2e-tests.sh --file e2e/docs/test_ui_form_controls.py --serving-mode=static`, `scripts/run-e2e-tests.sh --file e2e/docs/test_hydration_preservation.py --serving-mode=static`, and a Playwright simulation of Cloudflare `email-decode.min.js` DOM splitting yielding 0 hydration mismatch logs).

## Workflow follow-up

- Review and commit the OpenSpec change proposal artifacts once approved.
- Run `openspec-apply-change` (recording task completion on the implementation/test branch), `openspec-sync-specs` to merge `specs/elements/spec.md` into `openspec/specs/elements/spec.md`, and `openspec-archive-change` to move this change into `openspec/changes/archive/` before PR submission.
- Verify `npx @fission-ai/openspec@latest validate --specs --changes` and `python3 scripts/check-doc-spec-refs.py` pass after archiving.
