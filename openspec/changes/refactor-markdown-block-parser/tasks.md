# Tasks: refactor-markdown-block-parser

Implementation strategy (per design D12): the block layer is a **structural port**
of the reference two-phase algorithm (commonmark.py `blocks.py` + the appendix and
prose sections of the vendored `tests/conformance/.tmp/gfm_spec.txt`). Do NOT draft
the driver from memory. After each block kind lands, run the matching spec section
through the conformance harness and confirm expected flips before proceeding.

Until task A10 the new module is NOT wired into `DefaultMarkdownParser`; the repo
stays green at every commit. Each A-task is one commit.

## Session A: block parser

- [x] A0 Read the reference material end-to-end before writing code: commonmark.py
  `blocks.py` (driver, `BlockStarts`, `parse_list_marker`, tight/loose logic) and
  the spec.txt sections Tabs / Block quotes / List items / Lists / Appendix.
  Then create `webcompy/template/_markdown_blocks.py` with: the `_Block` model,
  the `(offset, column, next_nonspace, indent, blank, partially_consumed_tab)`
  cursor (`advance_offset` / `find_next_nonspace` / `advance_next_nonspace` /
  `add_line` incl. partial tabs and NUL replacement), the `Parser` driver
  (`incorporate_line`, `close_unmatched_blocks`, `add_child`, `finalize`) with
  document + paragraph only, and an HTML renderer for document/paragraph.
  Validate against the Paragraphs and Blank lines spec sections
- [x] A1 Port block_quote (first container; validates the continuation descent and
  lazy continuation). Validate against the Block quotes spec section
- [x] A2 Port ATX headings (space-required, closing sequences, 0-3 indent,
  7+ hashes rejected), setext headings (block-start conversion of the open
  paragraph, with link-ref resolution first), and thematic breaks (incl. spaced
  variants). Validate against ATX headings / Setext headings / Thematic breaks
- [x] A3 Port indented code blocks (4-column rule, paragraph-interruption rule,
  blank-line handling) and verify tab behavior end-to-end (partial tabs in
  container and code contexts). Validate against Indented code blocks and Tabs
- [x] A4 Port lists and list items: `parse_list_marker` (W+N padding rules,
  paragraph-interruption rules: ordered must start with 1, empty first item may
  not interrupt), `lists_match` (bullet char / ordered delimiter consistency,
  `<ol start="N">` when N != 1), tight/loose via `ends_with_blank_line`, block
  children inside items. This is the largest task; port the reference logic
  without simplification. Validate against List items / Lists / Precedence
- [x] A5 Port fenced code blocks (``` and ~~~, backtick-fence info may not contain
  a backtick, closing fence same char and >= opening length, fence offset
  stripping with partial tabs, info string first word entity-decoded →
  `class="language-*"`, closing fence returns the continue_=2 early exit).
  Validate against Fenced code blocks
- [x] A6 Port HTML blocks: all seven GFM types (type 1 includes `textarea` per
  GFM spec.txt; type 6 tag list transcribed from spec.txt; type 7 may not
  interrupt a paragraph; types 1-5 end on their close condition checked after
  add_line; types 6-7 end on blank line). Validate against HTML blocks
- [x] A7 Implement link reference definition parsing in the block layer
  (label/destination/title grammar incl. multi-line titles, first-definition-wins,
  absorption removes them from paragraph output) and retain the table on the
  parse result for the inline rewrite. Validate against Link reference definitions
- [ ] A8 Add GFM tables: at paragraph finalization, second line is a valid
  delimiter row (cells = trimmed `:?-+:?`, cell count equals header count) →
  convert to a table block; row splitting on unescaped pipes (`\|` skipped);
  excess cells dropped, missing cells filled empty; alignment emitted as
  `align="left|center|right"` per delimiter colons; no `<tbody>` when no body
  rows. Validate against Tables (extension)
- [x] A9 Add GFM task list items: at list-item finalization, a leading
  `[ ]`/`[x]`/`[X]` marker followed by whitespace is stripped from the first
  paragraph and recorded; rendering emits
  `<input checked="" disabled="" type="checkbox"> ` (checked only when set;
  cmark-gfm attribute order, no self-closing slash) at the start of the item's
  first paragraph content. Validate against Task list items (extension)
- [ ] A10 Switch `DefaultMarkdownParser.render()` to the new module (dedent
  multi-line sources only, per D11; move `_inline` behind the narrow seam).
  Then flip the conformance xfails: run the suite, remove every XPASS number
  from `tests/conformance/xfail.json`, keep `baseline` counts consistent
  (`xfailing == len(xfail_examples)`, `passing + xfailing == 672`), add a
  `notes` field mapping remaining block-section xfail numbers to inline-cause
  explanations (loader + `test_gfm_spec.py` reason + a validation test that
  every block-section xfail has a note). Update `tests/test_markdown_parser.py`
  expectations to cmark-gfm emission (incl. `<hr />`, newline-joined blocks,
  blockquote `<p>` wrapping, multi-line component tags now escaped paragraphs)
  and remove the retired `gfm_deviation` block tests. Investigate any
  previously-passing example that regresses before considering an xfail addition

## Session B: integration and verification

- [ ] B1 Re-point `_markdown_for._is_list_body` at the ported list-marker matcher
  (single source of truth) with `textwrap.dedent` applied to the body BEFORE
  matching (pre-dedent template sources must still detect); extend
  `_protected_spans`' fence detection to `~~~`; add a test that task-list bodies
  (`- [ ] {{ item }}`) are detected as list bodies (design open question 2: yes)
- [ ] B2 Re-verify `MarkdownForElement` end-to-end (`test_markdown_for.py` green;
  merged `<ul>`/`<ol>` structure identical; per-item static `{% if %}` preserved)
  and verify `{{ }}`/`{% %}` code protection still holds for fenced and indented
  code (`TestMarkdownCodeBlockTemplateProtection` stays green)
- [ ] B3 Deep-nesting stress test (blockquotes/lists ~100 levels) proving
  iterative (non-recursive) driver operation within Python/Pyodide stack limits
- [ ] B4 `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` clean;
  `uv run python -m pytest tests/ --tb=short` green; conformance rate recorded
  for the PR; check `.opencode/agents/ci-review.md` invariants (expected: no
  change needed — markdown internals only)
- [ ] B5 `uv run python -m webcompy generate` on docs_app succeeds
- [ ] B6 Run every E2E group SEQUENTIALLY, one at a time (never `--parallel`):
  `scripts/run-e2e-tests.sh bootstrap-static`, `components`, `reactive-lists`,
  `dynamic-control`, `router`, `interaction`, `bundled-deps`, `runtime-local`,
  `standalone`, `plugin-script`, `template`, `docs-home`, `docs-demos`,
  `docs-matplotlib`, `docs-fetch` — all must pass
- [ ] B7 `openspec validate refactor-markdown-block-parser --strict` passes; run
  the openspec-verify-change skill and report findings (spec sync and archive
  are explicitly out of scope, per user instruction)
