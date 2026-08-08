# Tasks: feat-markdown-document-support

## 1. Frontmatter Parsing

- [x] 1.1 Create `packages/webcompy/src/webcompy/template/_frontmatter.py` with `split_frontmatter(source: str) -> tuple[dict[str, Any], str]` handling `---` (flat key-value) and `+++` (TOML via `tomllib`) delimiters; raise `WebComPyException` for malformed blocks
- [x] 1.2 Add unit tests `tests/test_frontmatter.py`: flat extraction, TOML nested structures, no-frontmatter passthrough, malformed flat line, invalid TOML, unterminated block

## 2. Post-Bind Transforms

- [x] 2.1 Create `packages/webcompy/src/webcompy/template/_markdown_transforms.py` with a defensive element-tree walk (handles `_children` and `_pending_children`, follows the `_suspense.py` walk pattern)
- [x] 2.2 Implement slug generation (Unicode-aware lowercase, whitespace→`-`, strip non-alphanumeric except `-`, `-2`/`-3` dedupe) and `apply_heading_ids(element)`
- [x] 2.3 Implement `collect_headings(element) -> tuple[HeadingInfo, ...]` resolving text from `TextElement`/`Computed` descendants in document order
- [x] 2.4 Implement `replace_code_blocks(element)` swapping `<pre><code class="language-*">` subtrees for `CodeBlock({"code": text, "lang": lang})` preserving literal code content
- [x] 2.5 Implement `apply_class_map(element, classes)` merging mapped classes into matching tags additively
- [x] 2.6 Add unit tests `tests/test_markdown_transforms.py`: slug rules (ASCII, CJK, duplicates, punctuation), id injection on/off, TOC order/levels/interpolated text, code replacement on/off, literal `{{ }}` in fences, class merge behavior, `{% if %}`/`{% for %}` subtrees

## 3. render_markdown Options

- [ ] 3.1 Add keyword-only `heading_ids: bool = False`, `code_blocks: bool = False`, `classes: Mapping[str, str] | None = None` to `render_markdown` in `packages/webcompy/src/webcompy/template/__init__.py`, applying the corresponding transforms post-bind
- [ ] 3.2 Add unit tests covering each option end-to-end via `render_markdown` and verify default output is byte-identical to current behavior

## 4. load_markdown_document

- [ ] 4.1 Create `packages/webcompy/src/webcompy/template/_markdown_document.py` with frozen dataclasses `HeadingInfo(level, text, id)` and `MarkdownDocument(content, metadata, toc)`
- [ ] 4.2 Implement async `load_markdown_document(source: str | Path, ...)`: `ResourcePort.load_text` → `split_frontmatter` → `render_markdown` with document transforms → `collect_headings` → `MarkdownDocument`
- [ ] 4.3 Export `load_markdown_document`, `MarkdownDocument`, `HeadingInfo` from `webcompy.template` (`__all__` and `.pyi` stubs if applicable)
- [ ] 4.4 Add unit tests `tests/test_markdown_document.py` using `webcompy_testing` (TestRenderer / fake resource port): full pipeline, metadata propagation, SSR resource recording, TOC/id consistency, usage inside `async def` component setup with `context.set_title`

## 5. prose.css Preset

- [ ] 5.1 Create `packages/webcompy/src/webcompy/ui/_styles/prose.css`: `.prose`-scoped rules in `@layer prose` for headings (incl. anchor affordance), paragraphs, lists, tables, blockquotes, `hr`, inline code; reference `tokens.css` variables only
- [ ] 5.2 Register `prose.css` in `_STYLES_FILES` (`ui/_styles/__init__.py`); confirm it is NOT imported by `index.css`
- [ ] 5.3 Add/adjust tests verifying `_STYLES_FILES` registration, dev-server serving, and SSG copy of `prose.css`

## 6. Verification & Docs

- [ ] 6.1 Run `uv run ruff check .` and `uv run ruff format --check .` — fix all findings
- [ ] 6.2 Run `uv run pyright` — fix all findings
- [ ] 6.3 Run `uv run python -m pytest tests/ --tb=short` including `tests/conformance/` — GFM conformance suite must pass unmodified
- [ ] 6.4 Update `AGENTS.md` File → Spec Mapping (`webcompy/template/` row gains `markdown-document/spec.md`), Framework Invariants if needed, and Current Specs list; update `.opencode/skills/webcompy-review/SKILL.md` invariant references in sync
- [ ] 6.5 Run `python3 scripts/check-doc-spec-refs.py` and `openspec validate feat-markdown-document-support` — both must pass
