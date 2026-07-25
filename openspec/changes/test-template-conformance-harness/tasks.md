# Tasks: test-template-conformance-harness

## 1. GFM Spec Harness

- [x] 1.1 Pin the official GFM `spec.txt` to a specific cmark-gfm commit (URL + SHA-256) as constants in `tests/conformance/_spec_examples.py`; implement on-demand download with SHA-256 verification and cache at `tests/conformance/.tmp/gfm_spec.txt` (gitignored). Fail with clear error when cache is missing AND network is unavailable.
- [x] 1.2 Implement the example extractor (`tests/conformance/_spec_examples.py`): parse `example` fences into `(number, section, markdown, expected_html)` tuples; unit-test the extractor itself (counts, section names, edge cases)
- [x] 1.3 Implement the parametrized pytest suite (`tests/conformance/test_gfm_spec.py`): one test per example running `DefaultMarkdownParser.render()`, comparison normalized only for trailing whitespace/newlines
- [x] 1.4 Create the strict-xfail list mechanism (`tests/conformance/xfail.txt` + loader); mark every currently-failing example; add `test_gfm_conformance_rate` summary reporting pass/total without failing

## 2. Deviation Inventory

- [x] 2.1 Mark existing deviation-pinning tests in `tests/test_markdown_parser.py` (space-less headings, ignored fence language, tab→2-spaces, and any others found) with `pytest.mark.gfm_deviation`; register the marker in pytest config
- [x] 2.2 Record the full deviation list in the `markdown-conformance` spec (cross-check against the harness xfail list so every deviation maps to failing spec examples)

## 3. HTML Parser Environment Parity

- [x] 3.1 Add a unit-tier helper that renders a fixed set of version-sensitive templates (`<textarea>` with markup-like content, `<title>`, `<pre>`, charref edge cases, `<plaintext>`) via `render_template` and serializes the resulting tree for comparison
- [x] 3.2 Add one E2E scenario (existing Playwright infra, appended to a suitable group) rendering the same template set in the browser and comparing against the server serialization
- [x] 3.3 Run the parity check; if divergence is found, implement framework-side pinning in `webcompy/template/_parser.py` (explicit RCDATA handling for `textarea`/`title`, `CDATA_CONTENT_ELEMENTS` override) with unit tests
- [x] 3.4 Record the parity verdict (and pin, if applied) in the design doc's Open Questions section and the spec scenario outcomes

## 4. Spec Documentation of Limitations

- [x] 4.1 Verify each documented limitation against the actual code behavior (expression grammar, for-loop semantics, scoped-CSS dead rules/last-wins/dropped at-rules/global keyframes, SVG casing, dedent×pre, no `{# #}`, entity-decoded holes); adjust spec wording where reality differs
- [x] 4.2 Update `.opencode/agents/ci-review.md` file→spec mapping for the new `markdown-conformance` spec

## 5. Verification

- [x] 5.1 `uv run ruff check .` and `uv run ruff format .` clean
- [x] 5.2 `uv run pyright` clean
- [x] 5.3 `uv run python -m pytest tests/ --tb=short` green (harness included; deviation marker selectable via `-m gfm_deviation`)
- [x] 5.4 Conformance rate captured in the PR description as the rewrite baseline (16.2%, 109/672)
- [x] 5.5 `scripts/run-e2e-tests.sh <parity group>` green (all 15 groups × 2 modes = 30 successes)
- [x] 5.6 `openspec validate test-template-conformance-harness --strict` passes
