# Tasks: fix-teleport-anchor-layout-shift

## 1. Teleport anchor becomes a comment node (D1, D2)

- [x] 1.1 In `webcompy/elements/types/_teleport.py`, replace `_ANCHOR_TEXT = "\u200b"` with `_ANCHOR_DATA = "webcompy-teleport-anchor"` and rewrite `_create_node()` to `inject(DOM_PORT_KEY).create_comment(self._ANCHOR_DATA)` for all environments (remove the `ENVIRONMENT` branch)
- [x] 1.2 Update `_node_matches_existing()` to require `nodeName == "#comment"` and `textContent == _ANCHOR_DATA`; update `_adopt_node()` to keep the marker data (drop the text-clearing behavior)
- [x] 1.3 Keep the defensive recreate-anchor path in `_hydrate_node()` unchanged; confirm `_node_count`, `_mount_node`, `_mounted_direct_count`, and shared-target re-indexing are node-kind-agnostic (no edits expected)

## 2. DOMPort.create_comment across implementations (D4)

- [x] 2.1 Add `create_comment(data: str) -> DOMNode` as an abstract method to `DOMPort` in `webcompy/ports/_dom.py`
- [x] 2.2 Implement `BrowserDOMPort.create_comment()` via `document.createComment(data)` in `webcompy/ports/_browser/_dom.py`
- [x] 2.3 Implement `ServerDOMPort.create_comment()` returning `VirtualDOMNode("#comment", node_type=8, text_content=data)` in `webcompy_server/ports/_dom.py`
- [x] 2.4 Add an explicit `create_comment()` to `FakeBrowserDOMPort` in `webcompy_testing/_ports.py` (same construction as the server port)

## 3. Server virtual DOM comment support (D4)

- [x] 3.1 In `webcompy_server/ports/_virtual_dom.py`, make `nodeName` return `"#comment"` for `node_type == 8` (verify `textContent` getter/setter already covers it)
- [x] 3.2 In `webcompy_server/ports/_dom.py` `_serialize_node()`, add a `nodeType == 8` branch emitting `<!--{textContent}-->` before the element branch

## 4. Unit test updates

- [x] 4.1 `tests/test_teleport.py`: swap `\u200b` fixtures/assertions for the comment marker (lines ~498, 540, 555, 633, 710); assert `"\u200b" not in html_str` alongside the comment assertion in the SSR test
- [x] 4.2 Add `handle_comment` to `_FakeDOMParser` so round-trip hydration tests parse comment anchors into `FakeDOMNode("#comment", node_type=8, ...)`
- [x] 4.3 Update `test_hydration_after_ssr_keeps_siblings_single_and_adopts_anchor` to expect node order `["P", "#comment", "P"]` with the comment adopted (identity + `__webcompy_prerendered_node__`)
- [x] 4.4 Rewrite `test_hydration_with_bare_text_siblings_recreates_anchor_in_order` for the no-merge semantics: parsed tree has three distinct nodes (text / comment / text), hydration adopts each in index order, each sibling appears exactly once, and the teleport schedules its own render
- [x] 4.5 Add a regression unit test: SSR-render a teleport whose logical sibling is a block-level element (navbar-like structure) and assert the output contains `<!--webcompy-teleport-anchor-->` and no `\u200b`

## 5. E2E layout regression (D5)

- [ ] 5.1 In `e2e/docs/test_home.py`, add a test that navigates with `wait_until="domcontentloaded"` (raw `page` fixture, no pyscript-init wait), measures `offsetHeight` of the first `.navbar-item` and of each `.navbar-item-dropdown`, and asserts they are equal
- [ ] 5.2 Run the docs-home E2E group and confirm the new test passes (and would fail against the old ZWSP anchor)

## 6. Verification and spec sync

- [ ] 6.1 `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`
- [ ] 6.2 `uv run python -m pytest tests/ --tb=short` (full suite, teleport subset green)
- [ ] 6.3 `scripts/run-e2e-tests.sh docs-home` and `scripts/run-e2e-tests.sh docs-documents`
- [ ] 6.4 `openspec validate fix-teleport-anchor-layout-shift --strict` and `python3 scripts/check-doc-spec-refs.py`
- [ ] 6.5 Sync the three delta specs into `openspec/specs/{teleport,virtual-dom,port-abstraction}/spec.md`
- [ ] 6.6 Update `AGENTS.md` invariant/spec tables if any spec headings or references changed (run the check script again afterwards)
