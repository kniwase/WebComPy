## 1. VDOM Unit Tests (TDD — write failing tests first)

- [ ] 1.1 Write test: `_mount_node()` reinserts detached node when `_mounted=True` and `parentNode=None`
- [ ] 1.2 Write test: `_preserve_children=True` skips excess-child cleanup in `_render()`
- [ ] 1.3 Write test: `_preserve_children=True` skips excess-child cleanup in `_hydrate_node()`
- [ ] 1.4 Write integration test: SwitchElement patch preserves external nodes and recovered text nodes

## 2. Layer 1 — `_mount_node()` Detached Node Recovery

- [ ] 2.1 Add `elif` branch to `_mount_node()` in `_abstract.py` for `_mounted=True` + `parentNode=None` case
- [ ] 2.2 Run unit tests: Task 1.1 SHALL pass

## 3. Layer 2 — `:preserve_children` Attribute

- [ ] 3.1 Add `PreserveChildrenKey` type and `create_element()` extraction in `generators.py`
- [ ] 3.2 Add `_preserve_children: bool` field to `Element.__init__()` in `_element.py`
- [ ] 3.3 Guard `_render()` cleanup loop with `_preserve_children` in `_base.py`
- [ ] 3.4 Guard `_hydrate_node()` cleanup loop with `_preserve_children` in `_base.py`
- [ ] 3.5 Thread `_preserve_children` through `Component.__init_component()` in `_component.py`
- [ ] 3.6 Ensure `_preserve_children` is never rendered as a DOM attribute in `_get_processed_attrs()` and `_adopt_node()`
- [ ] 3.7 Run unit tests: Tasks 1.2 and 1.3 SHALL pass
- [ ] 3.8 Run integration test: Task 1.4 SHALL pass

## 4. App-Side Changes — SyntaxHighlighting Enhancement

- [ ] 4.1 Add input validation (`_validate_code`: size limit, null-byte detection, type check)
- [ ] 4.2 Update `SyntaxHighlighting` props: `code: str | SignalBase[str]`
- [ ] 4.3 Wire `SignalBase` path: `on_after_updating` for reactive re-highlight
- [ ] 4.4 Switch from `hljs.highlightElement()` to `hljs.highlight()` + `code_ref.element.innerHTML`
- [ ] 4.5 Use `:preserve_children: True` on `<code>` element, remove `TextElement` child
- [ ] 4.6 Simplify `DemoDisplay`: remove hljs logic, delegate to `SyntaxHighlighting({"code": source_code, "lang": "python"})`
- [ ] 4.7 Verify `home.py` call sites still work (static `str` props unchanged)
- [ ] 4.8 Verify docs_app generates correctly via `webcompy generate`

## 5. Verification

- [ ] 5.1 Run `uv run ruff check .` (lint)
- [ ] 5.2 Run `uv run ruff format .` (format check)
- [ ] 5.3 Run `uv run pyright` (type check)
- [ ] 5.4 Run `uv run python -m pytest tests/ --tb=short` (unit tests)
- [ ] 5.5 Run E2E tests: `scripts/run-e2e-tests.sh`
- [ ] 5.6 Update `.opencode/agents/ci-review.md` with new file→spec mapping for `element-preserve-children` and `syntax-highlighting-component`
