# Design: test-template-conformance-harness

## Context

Two upcoming changes (`refactor-markdown-block-parser`, `refactor-markdown-inline-parser`) will replace the regex-based `DefaultMarkdownParser` with a multi-stage parser targeting full GFM conformance. Such a rewrite needs a measurement baseline that exists *before* the new parser, so progress is objective (conformance rate N/total) and regressions in already-passing examples are caught immediately.

Independently, an audit of the template engine found that stdlib `html.parser` behavior differs across Python builds for RCDATA/raw-text elements (`<textarea>`, `<title>`, `<plaintext>`): recent CPython 3.12 security backports added RCDATA handling, but the Pyodide-bundled stdlib may behave differently. Since the same parser code runs in SSR and in the browser, a divergence would produce different Element trees for the same template and break hydration. This is currently a hypothesis, not a measured fact.

Finally, the audit classified many behaviors as *intentional limitations* (not defects), but they exist nowhere in written form — only in chat history. Without spec documentation, future changes may "fix" them accidentally or be blocked by reviewers lacking context.

## Goals / Non-Goals

**Goals:**
- Objective, offline GFM conformance measurement for `DefaultMarkdownParser.render()`.
- Cross-environment HTML parser parity verdict (and fix if the verdict is negative).
- Written, spec-level inventory of intentional template-engine limitations.

**Non-Goals:**
- Improving the conformance rate (that is the rewrites' job).
- Changing any parser behavior (except the conditional parity pin).
- User-facing docs.

## Decisions

### D1. Pin the official GFM `spec.txt` to a specific commit; download on-demand with hash verification

The GFM spec publishes a single `spec.txt` with examples delimited by 32-backtick `example` fences (input / expected HTML separated by `.`), numbered sequentially. The harness records the spec revision (cmark-gfm commit SHA) and SHA-256 hash as module constants in `tests/conformance/_spec_examples.py`. At first use, the file is fetched via stdlib `urllib.request`, verified against the SHA-256, and cached at `tests/conformance/.tmp/gfm_spec.txt` (gitignored via the existing `**/.tmp/` rule). The harness then parses the cached file into `(number, section, markdown, expected_html)` tuples at pytest collection.

- **Why fetched-on-demand, not vendored**: the spec.txt is derived from CommonMark (CC BY-SA 4.0). Committing the content into the repository raises CC BY-SA share-alike concerns. The hash-pinned cache achieves the same revision-pin guarantee (actually stronger — bit-exact verification) without distributing the content.
- **Why not a git submodule**: a submodule avoids the same distribution concern but adds the whole cmark-gfm repository (tens of MB, C sources) for one text file, requires `submodules: true` in CI, slows every clone, and conflicts with worktree workflows. The hash-pinned URL achieves the same legal effect with much less operational cost.
- **Alternative considered**: depend on a packaged copy (e.g. via a PyPI package) — rejected; adds a dependency for a static text file.
- **Failure mode when cache missing and network unavailable**: the harness fails the test run with a clear error message instructing the user to populate the cache. It does not silently skip — a missed conformance measurement is worse than a visible failure.

### D2. Parametrize one pytest test per spec example; track failures as explicit xfails

Each example becomes `test_gfm_spec[NNN-section]`. Failing examples are recorded in a checked-in xfail list (`tests/conformance/xfail.txt`, one example number per line) with `strict=True` — so an example that *starts* passing fails the suite until removed from the list. This makes conformance improvement self-acknowledging.

- **Why strict xfail over a numeric threshold**: a threshold silently hides regressions below the bar; the explicit list turns every improvement into a reviewed diff.
- A summary test (`test_gfm_conformance_rate`) reports the pass/total count for visibility without failing.

### D3. Normalization rules for comparison are defined in the harness, not the parser

The GFM expected outputs assume exact HTML strings. The harness compares `DefaultMarkdownParser.render()` output to expected HTML with documented normalizations only (trailing whitespace/newline). No semantic HTML canonicalization — if normalization is ever expanded, that is a reviewed harness change.

- **Known gap accepted**: examples whose expected output contains tags the template layer later rejects (`<script>` in HTML blocks) are still in scope — the conformance target applies to the Markdown→HTML string layer, not the template binding layer.

### D4. Deviation inventory as a spec appendix + test markers

Existing tests in `tests/test_markdown_parser.py` that pin non-GFM behavior (e.g. space-less heading `#hashtag` → `<h1>`, ignored fence language, tab→2-spaces) are marked with a `pytest.mark.gfm_deviation` marker and listed in the `markdown-conformance` spec as **scheduled for removal** in the parser-rewrite changes. No test deletion happens in this change (the current parser must stay green).

### D5. Parity verification via dual-render comparison, E2E for the browser leg

Parity is checked by rendering the same set of version-sensitive templates (`<textarea>` with markup-like content, `<title>`, `<pre>`, charref edge cases, `<plaintext>`) through `render_template` on CPython (unit tier) and in a real browser (one new E2E scenario using the existing Playwright infrastructure), comparing the resulting element-tree serialization.

- **If parity holds**: the E2E test becomes a permanent regression guard; no parser change.
- **If parity fails**: subclass-level pinning is added in `_parser.py` (override `CDATA_CONTENT_ELEMENTS` and implement RCDATA handling for `textarea`/`title` explicitly, e.g. via `set_cdata_mode`), making behavior version-independent. The pin is included in *this* change.
- **Why not pin preemptively**: unneeded behavior overrides are tech debt; measure first. (The pin is small and local if needed.)

### D6. Limitations documented as a `template-engine` spec appendix section

A "Known Limitations" set of ADDED requirements (phrased as SHALL NOT / non-support statements with rationale scenarios) is added to the `template-engine` delta, covering: expression grammar (identifier/dot paths only; no subscripts/calls/filters/comparisons), one-variable dict iteration yielding values, `:root`/`html`/`body` scoping dead-rules, duplicate CSS keys last-wins, `@import`/`@charset` dropped, global keyframe names, SVG/MathML case corruption, dedent×`<pre>` interaction, no `{# #}` comments, no literal-`{{` escape, entity-decoded holes.

- **Why in spec, not only docs_app**: specs are the review baseline; docs_app gets the user-facing version later (in the inline-parser change, once the Markdown sections reach final state).

### D7. Harness lives in the unit tier

`tests/conformance/` runs under the standard `pytest tests/` invocation (no `WEBCOMPY_RUN_E2E` gate, no browser, no network). This aligns with `test-execution-paths`: only the single parity scenario joins an E2E group.

## Risks / Trade-offs

- [Vendored spec.txt goes stale vs upstream GFM] → Version recorded in file header; updating it is a deliberate, reviewed change.
- [652+ examples slow the unit suite] → Extraction is pure text parsing; per-example tests are microsecond-scale parser runs. Measured during implementation; if needed, examples can be grouped per section.
- [Strict-xfail list churn during rewrites] → Intentional: each rewrite PR shows exactly which examples flipped.
- [Parity E2E adds a new browser scenario → CI time] → Single scenario appended to an existing E2E group, not a new group.
- [Marking tests `gfm_deviation` without deleting them may look like dead weight] → The marker is the deletion queue for changes B/C; removing them now would break the current parser's suite.

## Migration Plan

No user-facing changes (unless parity pinning triggers, which only makes browser behavior match server behavior — a strict improvement). CI picks up the new tests automatically.

## Open Questions

1. Pin recorded in code at implementation time: cmark-gfm commit `499789b49373bfa045d0e7547e5ee63444c77bca`, SHA-256 `7d8e5814befec287ac116786d81ff14e0adc9b13295b4494649e995408fd871c`, 672 examples. (Filled in at implementation; will be updated when the spec is re-pinned.)
2. Whether `<plaintext>` should join the rejected-tags list independent of parity results — deferred; current behavior is merely documented as a limitation.
