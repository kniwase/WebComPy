## 1. VirtualDOMNode implementation

- [ ] 1.1 Create `webcompy/ports/_server/_virtual_dom.py` with `VirtualDOMNode` class satisfying `DOMNode` Protocol — store `tag_name`, `attributes: dict`, `children: list`, `event_listeners: list`, `text_content`, `node_type`, `__webcompy_node__`, `_parent`
- [ ] 1.2 Implement tree operations: `appendChild`, `removeChild`, `insertBefore`, `replaceChild`, `remove` — manage children list and parent references
- [ ] 1.3 Implement attribute operations: `setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`
- [ ] 1.4 Implement event operations: `addEventListener`, `removeEventListener` — store as `(event_name, handler)` tuples
- [ ] 1.5 Implement properties: `childNodes` (returns list), `textContent` (get/set), `nodeName` (returns tag_name), `nodeType` (1=element, 3=text)

## 2. ServerDOMPort rewrite

- [ ] 2.1 Rewrite `webcompy/ports/_server/_dom.py` — replace exception-throwing stubs with virtual DOM factory: `create_element()` returns `VirtualDOMNode`, `create_text_node()` returns virtual text node
- [ ] 2.2 Implement `ServerDOMPort.render_html(node: DOMNode) -> str` — traverse virtual tree, serialize to HTML string
- [ ] 2.3 Implement HTML serialization rules: HTML-escape text content and attribute values, self-close void elements (`br`, `hr`, `img`, `input`, `link`, `meta`, `source`, `area`, `base`, `col`, `embed`, `track`, `wbr`), omit `None`-valued attributes
- [ ] 2.4 Verify `render_html()` produces identical output to current `_render_html()` methods — generate docs_app with both paths and diff results

## 3. Unify render path in element base classes

- [ ] 3.1 Remove `_render_html()` abstract method from `ElementAbstract` in `webcompy/elements/types/_abstract.py`
- [ ] 3.2 Remove `_render_html()` from `ElementWithChildren` in `webcompy/elements/types/_base.py`
- [ ] 3.3 Update `ElementBase._init_node()` in `_element.py` — remove `else: raise WebComPyException` branch; both browser and server now use `_create_node()` which delegates to `inject(DOM_PORT_KEY)`
- [ ] 3.4 Update `TextElement._init_node()` in `_text.py` — same unification

## 4. Remove _render_html() from element subclasses

- [ ] 4.1 Remove `_render_html()` from `Element` in `webcompy/elements/types/_element.py`
- [ ] 4.2 Remove `_render_html()` from `TextElement` and `NewLine` in `webcompy/elements/types/_text.py`
- [ ] 4.3 Remove `_render_html()` from `SwitchElement` in `webcompy/elements/types/_switch.py`
- [ ] 4.4 Remove `_render_html()` from `RepeatElement` in `webcompy/elements/types/_repeat.py`
- [ ] 4.5 Remove `_render_html()` from `DynamicElement` in `webcompy/elements/types/_dynamic.py`

## 5. Update server-side rendering entry points

- [ ] 5.1 Update SSG generation code to use `ServerDOMPort.render_html(root_node)` instead of calling element `_render_html()` directly
- [ ] 5.2 Update `webcompy/cli/_generate.py` if it references `_render_html()`
- [ ] 5.3 Update `webcompy/cli/_html.py` if it references `_render_html()`

## 6. Element system adapter for server DOMPort

- [ ] 6.1 In `ElementBase._create_node()`, add `DomNodeRef.__init_node__()` call so virtual nodes can satisfy `DOMNode` contract
- [ ] 6.2 In `ElementBase._init_new_node()`, verify `setAttribute` / `addEventListener` work on `VirtualDOMNode`
- [ ] 6.3 Make `DomNodeRef` compatible with `VirtualDOMNode` (current `__init_node__` expects `DOMNode` Protocol — should work)

## 7. Tests

- [ ] 7.1 Write tests for `VirtualDOMNode` — tree construction, attribute operations, event listener recording
- [ ] 7.2 Write tests for `ServerDOMPort.render_html()` — element serialization, void tags, attribute escaping, text escaping, nested trees
- [ ] 7.3 Write tests for unified render path — render the same component tree in both browser mock and server DOMPort, verify identical structure
- [ ] 7.4 Update existing SSG tests — migrate from HTML string comparison to virtual tree structure inspection where beneficial; keep string comparison as integration tests
- [ ] 7.5 Write tests for server-side rendering of components with attributes, event handlers, conditional branches, and list rendering
- [ ] 7.6 Run existing test suite and fix regressions

## 8. Cleanup

- [ ] 8.1 Search codebase for any remaining `_render_html` references — ensure all are removed or migrated
- [ ] 8.2 Remove any `_render_html`-specific test utilities or helpers
- [ ] 8.3 Update type stubs if `_render_html` appears in any `.pyi` files

## 9. Verification

- [ ] 9.1 Run lint: `uv run ruff check .`
- [ ] 9.2 Run type check: `uv run pyright`
- [ ] 9.3 Run unit tests: `uv run python -m pytest tests/ --tb=short`
- [ ] 9.4 Run SSG and verify output: `uv run python -m webcompy generate --app docs_app.bootstrap:app`
- [ ] 9.5 Diff generated docs against baseline to confirm no output regressions
- [ ] 9.6 Verify dev server starts: `uv run python -m webcompy start --dev --app docs_app.bootstrap:app`
