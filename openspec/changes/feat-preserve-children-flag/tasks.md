## 1. VDOM Unit Tests (TDD — write failing tests first)

- [x] 1.1 Write test: `_mount_node()` reinserts detached node when `_mounted=True` and `parentNode=None`
- [x] 1.2 Write test: `_preserve_children=True` skips excess-child cleanup in `_render()`
- [x] 1.3 Write test: `_preserve_children=True` skips excess-child cleanup in `_hydrate_node()`
- [x] 1.4 Write integration test: SwitchElement patch preserves external nodes and recovered text nodes

## 2. Layer 1 — `_mount_node()` Detached Node Recovery

- [x] 2.1 Add `elif` branch to `_mount_node()` in `_abstract.py` for `_mounted=True` + `parentNode=None` case
- [x] 2.2 Run unit tests: Task 1.1 SHALL pass

## 3. Layer 2 — `:preserve_children` Attribute

- [x] 3.1 Add `PreserveChildrenKey` type and `create_element()` extraction in `generators.py`
- [x] 3.2 Add `_preserve_children: bool` field to `Element.__init__()` in `_element.py`
- [x] 3.3 Guard `_render()` cleanup loop with `_preserve_children` in `_base.py`
- [x] 3.4 Guard `_hydrate_node()` cleanup loop with `_preserve_children` in `_base.py`
- [x] 3.5 Thread `_preserve_children` through `Component.__init_component()` in `_component.py`
- [x] 3.6 Ensure `_preserve_children` is never rendered as a DOM attribute in `_get_processed_attrs()` and `_adopt_node()`
- [x] 3.7 Run unit tests: Tasks 1.2 and 1.3 SHALL pass
- [x] 3.8 Run integration test: Task 1.4 SHALL pass

## 4. App-Side Changes — SyntaxHighlighting Enhancement

- [x] 4.1 Add input validation (`_validate_code`: size limit, null-byte detection, type check)
- [x] 4.2 Update `SyntaxHighlighting` props: `code: str | SignalBase[str]`
- [x] 4.3 Wire `SignalBase` path: `on_after_updating` for reactive re-highlight
- [x] 4.4 Switch from `hljs.highlightElement()` to `hljs.highlight()` + `code_ref.element.innerHTML`
- [x] 4.5 Use `:preserve_children: True` on `<code>` element, remove `TextElement` child
- [x] 4.6 Simplify `DemoDisplay`: remove hljs logic, delegate to `SyntaxHighlighting({"code": source_code, "lang": "python"})`
- [x] 4.7 Verify `home.py` call sites still work (static `str` props unchanged)
- [x] 4.8 Verify docs_app generates correctly via `webcompy generate`

## 5. SPA Navigation Bug Investigation

### 5.1 Bug Discovery
- [x] 5.1.1 Confirm bug: Code card disappears after SPA navigation between demo pages
- [x] 5.1.2 Verify direct page loads work correctly (all 3 cards visible)
- [x] 5.1.3 Document DOM structure difference: direct load vs SPA nav

### 5.2 Hypothesis Testing
- [x] 5.2.1 Test H1: `:preserve_children` conflict — removed flag, bug persists (❌)
- [x] 5.2.2 Test H2: `SyntaxHighlighting` component / external JS — replaced with plain PRE/CODE, bug persists (❌) (CONFIRMED: external JS is NOT the cause)
- [x] 5.2.3 Test H3: iframe influence — removed iframe, bug persists (❌)
- [x] 5.2.4 Test H4: Signal/on_after_rendering timing — used static string, bug persists (❌)
- [x] 5.2.5 Test H5: `_render()` cleanup loop — disabled loop, bug persists (❌)
- [x] 5.2.6 Test H6: Nested `.card` structure — flattened structure, bug disappears (✅)

### 5.3 Root Cause Analysis
- [ ] 5.3.1 Create minimal reproduction test with `TestRenderer`
- [ ] 5.3.2 Trace VDOM reconciliation during `SwitchElement._refresh()`
- [ ] 5.3.3 Identify exact failure point in `_patch_children()` or `_render()`

### 5.4 Fix Implementation
- [ ] 5.4.1 Apply targeted fix to identified reconciliation logic
- [ ] 5.4.2 Verify fix with minimal test case
- [ ] 5.4.3 Verify fix with full demo pages

### 5.5 Regression Testing
- [ ] 5.5.1 Run `tests/test_preserve_children.py`
- [ ] 5.5.2 Run E2E tests for demo pages
- [ ] 5.5.3 Run full test suite (`uv run python -m pytest tests/ --tb=short`)
- [ ] 5.5.4 Run lint and type check

## 6. Verification (Original)

- [x] 6.1 Run `uv run ruff check .` (lint)
- [x] 6.2 Run `uv run ruff format .` (format check)
- [x] 6.3 Run `uv run pyright` (type check)
- [x] 6.4 Run `uv run python -m pytest tests/ --tb=short` (unit tests)
- [x] 6.5 Run E2E tests: `scripts/run-e2e-tests.sh`
- [x] 6.6 Update `.opencode/agents/ci-review.md` and `AGENTS.md` with new file→spec mapping for `element-preserve-children`
