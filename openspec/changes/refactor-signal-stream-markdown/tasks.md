# Tasks: refactor-signal-stream-markdown

## 1. Markdown Content

- [x] 1.1 Create `docs_app/documents/signal_stream.md` with frontmatter (`title: Signals and Streams`, `description`) and body converted from the current component: H1 "Signals and Streams" + intro paragraph, H2 sections `to_signal: one-shot values`, `to_reactive_list: accumulating feeds`, `to_async_iter: consuming signal updates`, `Queue policy and lifecycle`; inline code as backticks, the four code examples as `python` fenced blocks, `**`/`*` for strong/emphasis (prose preserved verbatim)

## 2. Page and Manifest

- [ ] 2.1 Rewrite `docs_app/pages/document/signal_stream.py` as an async component that awaits `load_markdown_document("documents/signal_stream.md")`, sets the title from the frontmatter title, and returns `docs_page_template(doc, context.props.path)` with `DOCS_PAGE_SCOPED_STYLE` (mirroring `installation.py`)
- [ ] 2.2 Update the Guides entry in `docs_app/docs_manifest.py`: label "Signals and Streams", replace `component` with `source: "documents/signal_stream.md"` (path unchanged)
- [ ] 2.3 Delete `docs_app/templates/document/signal_stream.py` and confirm no remaining imports of `SignalStream`

## 3. E2E Updates

- [ ] 3.1 Update `e2e/docs/test_signal_stream.py`: browser title assertion to "Signals and Streams - WebComPy Docs", keep H1/sidebar assertions, add TOC aside assertions (visible, links to page heading ids)
- [ ] 3.2 Update `e2e/docs/test_quickstart.py`: pager Next link text and sidebar `aria-current` text to "Signals and Streams"
- [ ] 3.3 Update `e2e/docs/test_documents.py`: index card link name to "Open Signals and Streams"

## 4. Verification

- [ ] 4.1 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short`, and `python3 scripts/check-doc-spec-refs.py`
- [ ] 4.2 Run `scripts/run-e2e-tests.sh docs-documents` and `scripts/run-e2e-tests.sh docs-home` (both serving modes)
- [ ] 4.3 Run `openspec validate refactor-signal-stream-markdown --strict`
