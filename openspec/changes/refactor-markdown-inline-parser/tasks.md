# Tasks: refactor-markdown-inline-parser

## 1. Inline Scanner Foundations

- [x] 1.1 Create `webcompy/template/_markdown_inline.py`: node model (text, code span, raw HTML, autolink, delimiter run, bracket) and the character scanner emitting the node list; unit-test tokenization basics
- [x] 1.2 Backslash escapes and entity/numeric references (stdlib `html.entities.html5`), correct escape-then-resolve ordering, literal handling inside code — flip corresponding xfails
- [x] 1.3 Code spans (variable-length backtick matching, content normalization per spec) — flip xfails
- [x] 1.4 Hard/soft breaks (trailing spaces, backslash break) — flip xfails

## 2. Emphasis & Strikethrough

- [x] 2.1 Delimiter-run processing for `*` and `_` (odd-multiple-of-3 rule, intraword `_` restrictions, arbitrary nesting) — flip emphasis/strong xfails
- [x] 2.2 GFM strikethrough via the delimiter machinery (`~` runs) — flip xfails; remove legacy regex strikethrough

## 3. Links, Images & Autolinks

- [x] 3.1 Inline destinations (`<...>` and balanced-parens forms) and titles (`"`/`'`/`()`) — flip xfails
- [x] 3.2 Reference links (full/collapsed/shortcut, label normalization) using the block-layer definition table — flip xfails
- [x] 3.3 Images (alt text rendering rules per spec) — flip xfails
- [x] 3.4 Autolinks (`<scheme:>`, `<email>`) and GFM extended autolinks (`www.`, bare URLs/emails, boundary trimming) — flip xfails
- [x] 3.5 Route ALL link forms through the URL scheme allow-list; tests for `javascript:`/`data:`/`vbscript:` across inline, reference, and autolink forms

## 4. Raw HTML & Protection Port

- [x] 4.1 Raw inline HTML recognition per spec + GFM disallowed-raw-HTML escaping — flip xfails
- [x] 4.2 Remove the placeholder-based `{{ }}`/`{% %}` protection (structural guarantee: code content never enters inline parsing); keep all protection tests from fix-template-engine-defects green; add fuzz cases (template syntax inside spans/blocks, adjacent spans)
- [~] 4.3 Adversarial-input tests (delimiter seas, deep bracket nesting) completing in linear time — mitigations in place (iterative renderer avoids RecursionError); dedicated tests added in follow-up

## 5. Integration & Conformance Completion

- [x] 5.1 Swap the block facade's inline seam to the new engine; remove the legacy inline code path
- [~] 5.2 Reduce xfail list from 295 to 18 (654/672 passing); remaining 18 are documented as known deviations with accurate notes (9 emphasis = cmark-gfm divergence matching ecosystem; 2 autolink = harness artifact; 6 block-layer = inherited from prior change; 1 raw HTML = obscure edge case). xfail list NOT emptied per decision (deviations accepted).
- [~] 5.3 `uv run python -m pytest tests/ --tb=short` green; conformance rate 654/672 (97.3%) with 18 documented deviations
- [x] 5.4 `uv run ruff check .`, `uv run ruff format .`, `uv run pyright` clean

## 6. Documentation & Final Sweep

- [x] 6.1 Add docs_app "Template engine limitations" page (expression language, for-loop semantics, scoped-CSS limits, HTML parsing limits, Markdown feature matrix incl. non-GFM non-goals), verified against final behavior
- [x] 6.2 Update docs_app Markdown-feature docs to the final supported set (GFM)
- [x] 6.3 `uv run python -m webcompy generate` on docs_app; diff-review generated output for unintended changes
- [x] 6.4 Run `scripts/run-e2e-tests.sh` (Markdown/template groups) green
- [x] 6.5 Update `.opencode/agents/ci-review.md` invariants if the inline engine introduces new contracts
- [x] 6.6 `openspec validate refactor-markdown-inline-parser --strict` passes
