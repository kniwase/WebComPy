# Tasks: refactor-markdown-block-parser

## 1. Foundations

- [ ] 1.1 Create `webcompy/template/_markdown_blocks.py` with the block tree model (container/leaf node types) and the `(offset, column)` cursor with CommonMark tab advancement incl. partial tabs; unit-test tab math against spec tab examples
- [ ] 1.2 Implement the open-block stack driver (continuation checks → block-start priority → line incorporation → lazy continuation → bottom-up finalization) per the CommonMark appendix algorithm

## 2. Leaf Blocks

- [ ] 2.1 ATX headings (space-required, closing sequences, 0-3 indent) — flip corresponding xfails
- [ ] 2.2 Thematic breaks incl. spaced variants; setext headings via paragraph finalization — flip xfails; remove `gfm_deviation` heading tests
- [ ] 2.3 Fenced code (``` and `~~~`, info string → `class="language-*"`, closing-length/char rules, tab preservation) — flip xfails; remove deviation tests
- [ ] 2.4 Indented code blocks (4-column rule, interruption rules, blank-line handling) — flip xfails
- [ ] 2.5 HTML blocks (all 7 types, spec end conditions, multi-line comments/declarations) — flip xfails
- [ ] 2.6 Link reference definitions (parse + absorb, retain table on parse result) — flip xfails

## 3. Containers

- [ ] 3.1 Blockquotes (nesting, lazy continuation, inner block elements) — flip xfails
- [ ] 3.2 Lists and list items (marker consistency, start numbers, tight/loose, block children, indentation rules) — flip xfails
- [ ] 3.3 GFM task list items (static checkbox emission, GFM marker rules) — flip xfails
- [ ] 3.4 GFM tables (delimiter-row detection at paragraph finalization, alignment, cell-count rules, cell inline rendering via carried-over inline layer) — flip xfails

## 4. Integration

- [ ] 4.1 Rewire `DefaultMarkdownParser.render()` as facade: dedent → block parse → inline render of leaf content (existing inline code behind a narrow seam) → HTML emission
- [ ] 4.2 Re-point `_markdown_for._is_list_body` at the block parser's list-item start condition (single source of truth); decide + test task-list bodies in `{% for %}` (design open question 2)
- [ ] 4.3 Re-verify `MarkdownForElement` end-to-end (`test_markdown_for.py` green; merged `<ul>`/`<ol>` output identical; `{% if %}` static evaluation per item preserved)
- [ ] 4.4 Verify `{{ }}`/`{% %}` code protection still holds for fenced and indented code (tests from fix-template-engine-defects stay green)
- [ ] 4.5 Deep-nesting stress test (blockquotes/lists ~100 levels) proving iterative (non-recursive) operation

## 5. Cleanup & Verification

- [ ] 5.1 Remove all retired `gfm_deviation` block tests; confirm `pytest -m gfm_deviation` selects only remaining inline deviations
- [ ] 5.2 Confirm every remaining block-section xfail carries an inline-cause note (spec scenario: block xfails flipped)
- [ ] 5.3 `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` clean
- [ ] 5.4 `uv run python -m pytest tests/ --tb=short` green; conformance rate recorded in PR
- [ ] 5.5 `uv run python -m webcompy generate` on docs_app succeeds; spot-check Markdown-using pages
- [ ] 5.6 Update `.opencode/agents/ci-review.md` if invariants changed (e.g., block-parser contracts)
- [ ] 5.7 `openspec validate refactor-markdown-block-parser --strict` passes
