# Tasks

## 1. Directive Classification (Parser)

- [x] 1.1 Add `_GENERIC_DIRECTIVE_RE` and `_KNOWN_UNSUPPORTED_DIRECTIVES` to `packages/webcompy/src/webcompy/template/_parser.py`; rewrite `_scan_text_for_directives` to dispatch supported / known-unsupported / unknown with concise `WebComPyException` messages (compile-time)
- [x] 1.2 Add unit tests: unsupported directives (`extends`, `block`, `macro`, `include`, `set`, etc.) raise with "not supported" message; unknown directive (`{% endfo %}`) raises "unknown directive"; `{% raw %}` literal path unaffected; `{%` in attribute values stays literal; markdown path rejects unsupported directives (add to `tests/test_template_parser.py` / `tests/test_template_markdown.py`)

## 2. Loop Metadata — Core (`render_template` path)

- [x] 2.1 Implement internal `LoopMetadata` class (plain-value attributes) in `packages/webcompy/src/webcompy/template/_binder.py`; extend `_extend_for_ctx` to inject `loop` (metadata assigned before loop vars so a user var named `loop` shadows it)
- [x] 2.2 Wire plain metadata into `_bind_for_static` (enumerate-based positions for list and dict paths)
- [x] 2.3 Wire plain metadata into the ReactiveList single-arg path of `_bind_for_reactive`
- [x] 2.4 Unit tests: all seven attributes over static list/dict; ReactiveList values correct after append/remove; nested-loop shadowing; user loop var named `loop` shadows metadata (add to `tests/test_template_integration.py` or new `tests/test_template_loop_metadata.py`)

## 3. Loop Metadata — ReactiveDict (Computed-backed)

- [x] 3.1 In `_bind_for_reactive`, route dict loops through the two-arg dict `repeat()` overload (including one-var loops) so callbacks receive the key
- [x] 3.2 Build shared per-loop `positions` and `length` Computeds over the source signal; per-item attribute Computeds (`index`/`index0`/`revindex`/`revindex0`/`first`/`last`) derived from `positions`
- [x] 3.3 Unit tests: metadata correct on initial render; after `ReactiveDict` add/remove/reorder, reused children observe updated positions/length/first/last; removed-key Computeds become unobserved (no stale updates)

## 4. Loop Metadata — MarkdownForElement

- [x] 4.1 Inject `__wmdf_{n}_loop` plain metadata into `augmented_ctx` and extend `_rename_in_expressions` usage to rename `loop` in expressions in `packages/webcompy/src/webcompy/template/_markdown_for.py`
- [x] 4.2 Unit tests: `{{ loop.index }}` in markdown list-body for-loops renders positions; literal text "loop" outside expressions unaffected (add to `tests/test_markdown_for.py`)

## 5. Spec Consolidation and docs_app Removal

- [ ] 5.1 Expand `openspec/specs/template-engine/spec.md` Purpose with design intent (sugar over Element/Component system; Jinja2-inspired, not compatible; composition via components/slots; template inheritance permanently rejected)
- [ ] 5.2 Apply delta: add loop-metadata/shadowing/directive-rejection requirements; modify the four limitation requirements to be self-contained (sync via archive flow)
- [x] 5.3 Remove `docs_app` limitations page: route in `docs_app/router.py`, `docs_app/pages/document/limitations.py`, `docs_app/templates/document/limitations.py`
- [ ] 5.4 Check and update references: `AGENTS.md` File→Spec Mapping and `.opencode/skills/webcompy-review/SKILL.md` (mapping and invariants per spec changes)

## 6. E2E and Verification

- [ ] 6.1 Add e2e coverage: loop metadata rendering and reactive dict updates in `e2e/core/my_app/pages/` + `e2e/core/` (extend `test_template_control_flow.py`-style page); verify directive rejection surfaces as compile error
- [ ] 6.2 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short`
- [ ] 6.3 Run relevant e2e groups via `scripts/run-e2e-tests.sh` (template groups) and `uv run python -m webcompy generate` on docs_app to confirm the removed page breaks nothing
