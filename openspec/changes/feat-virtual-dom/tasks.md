## 1. VirtualDOMNode implementation

- [ ] 1.1 Create `webcompy/ports/_server/_virtual_dom.py` with `VirtualDOMNode` class satisfying `DOMNode` Protocol — store `tag_name`, `attributes: dict`, `children: list`, `event_listeners: list`, `text_content`, `node_type`, `__webcompy_node__`, `_parent`
- [ ] 1.2 Implement tree operations: `appendChild`, `removeChild`, `insertBefore`, `replaceChild`, `remove` — manage children list and parent references
- [ ] 1.3 Implement attribute operations: `setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`
- [ ] 1.4 Implement event operations: `addEventListener`, `removeEventListener` — store as `(event_name, handler)` tuples
- [ ] 1.5 Create `VirtualDOMEvent` class in `webcompy/ports/_server/_virtual_dom.py` — minimal `type`, `target`, `currentTarget`, `preventDefault` (no-op) for use with `VirtualDOMNode.dispatchEvent()`
- [ ] 1.6 Implement `dispatchEvent(event: VirtualDOMEvent) -> None` on `VirtualDOMNode` — fire stored handlers matching `event.type` synchronously so that signal updates and re-rendering propagate within the same call stack
- [ ] 1.7 Implement properties: `childNodes` (returns list), `textContent` (get/set), `nodeName` (returns tag_name), `nodeType` (1=element, 3=text)

## 2. ServerDOMPort rewrite

- [ ] 2.1 Rewrite `webcompy/ports/_server/_dom.py` — replace exception-throwing stubs with virtual DOM factory: `create_element()` returns `VirtualDOMNode`, `create_text_node()` returns virtual text node
- [ ] 2.2 Implement `ServerDOMPort.render_html(node: DOMNode) -> str` — traverse virtual tree, serialize to HTML string
- [ ] 2.3 Implement HTML serialization rules: HTML-escape text content and attribute values, output void elements without closing tags (e.g., `<br>`, `<img>`) per HTML5 convention, omit `None`-valued attributes
- [ ] 2.4 Verify `render_html()` produces identical output to current `_render_html()` methods — generate docs_app with both paths and diff results

## 3. Unify render path in element base classes

- [ ] 3.1 Remove `_render_html()` abstract method from `ElementAbstract` in `webcompy/elements/types/_abstract.py` — after cli/_html.py is migrated (task 5)
- [ ] 3.2 Remove `_render_html()` from `ElementWithChildren` in `webcompy/elements/types/_base.py`
- [ ] 3.3 Update `TextElement._update_text()` in `webcompy/elements/types/_text.py` — remove `if browser:` branch; both environments call `node.textContent = new_text` since `VirtualDOMNode` supports it
- [ ] 3.4 Remove `if not browser:` server branches from `_on_set_parent()` in element and router types — `_switch.py:84`, `_repeat.py:95`, `_view.py:25` (router). After virtual DOM unification, `render()` creates VirtualDOMNodes on the server via `ServerDOMPort`, so the server-only pre-creation logic inside these branches is no longer needed and would cause double creation
- [ ] 3.5 Verify that `_init_node()` (already unbranchified by `feat-port-abstraction`) works correctly with `VirtualDOMNode` on the server — both `ElementBase._init_node()` and `TextElement._init_node()` / `NewLine._init_node()` call `_create_node()` which delegates to `inject(DOM_PORT_KEY)` returning a `VirtualDOMNode`
- [ ] 3.6 Verify that `_detach_node()` (already unbranchified by `feat-port-abstraction`) works correctly with `VirtualDOMNode` on the server — `dom_port.create_text_node("")` returns a virtual text node and `parent_node.replaceChild(...)` operates on the virtual children list
- [ ] 3.7 Remove `if browser:` branch from `DynamicElement._render()` in `webcompy/elements/types/_dynamic.py` — after virtual DOM unification, `_position_element_nodes()` works on `VirtualDOMNode` (uses `appendChild`/`insertBefore` which `VirtualDOMNode` implements), so both environments use the same positioning logic
- [ ] 3.8 Remove environment guard from `RepeatElement._refresh()` in `webcompy/elements/types/_repeat.py:148` — change `if self._has_key and browser and self._children_keys:` to `if self._has_key and self._children_keys:`. After virtual DOM unification, `VirtualDOMNode` implements all DOM operations used by `_reconcile_children()` (`appendChild`, `insertBefore`, `remove`), so key-based reconciliation works identically on the server
- [ ] 3.9 Remove environment guard from `_component.py:172` — change `app._defer_depth > 0 and ENVIRONMENT == "pyscript"` to `app._defer_depth > 0`. After virtual DOM unification, both environments run `render()`, and the defer mechanism works correctly on the server via synchronous `schedule_macro_task()`. The guard is an unnecessary optimization that diverges from Decision 3's single-code-path goal

## 4. Router accessibility for testing

- [ ] 4.1 Modify `RouterLink._on_click()` in `webcompy/router/_link.py` — remove `ENVIRONMENT != "pyscript"` early return; instead, guard only the `pyscript` import, `pushState`, and `window.location` access inside a `if ENVIRONMENT == "pyscript"` block. `self._router.__set_path__(href, params)` executes unconditionally so that `dispatchEvent(VirtualDOMEvent("click"))` on a rendered RouterLink triggers full route transition (guards → navigate → after_route_change → SwitchElement route selection)

## 5. Remove _render_html() from element subclasses

- [ ] 5.1 Remove `_render_html()` from `TextElement` and `NewLine` in `webcompy/elements/types/_text.py`
- [ ] 5.2 Remove `_render_html()` from `DynamicElement` in `webcompy/elements/types/_dynamic.py`

## 6. Update server-side rendering entry points

- [ ] 6.1 Update SSG generation code to use `ServerDOMPort.render_html(root_node)` instead of calling element `_render_html()` directly
- [ ] 6.2 Update `webcompy/cli/_generate.py` if it references `_render_html()`
- [ ] 6.3 Update `webcompy/cli/_html.py` if it references `_render_html()`

## 7. Element system adapter for server DOMPort

- [ ] 7.1 Verify `DomNodeRef` is compatible with `VirtualDOMNode` — `DomNodeRef.__init_node__(node)` sets `self._node = node` and `node` must satisfy `DOMNode` Protocol; `VirtualDOMNode` already does
- [ ] 7.2 Verify `ElementBase._init_new_node()` works on `VirtualDOMNode` — `setAttribute` and `addEventListener` use `DOMNode` Protocol which `VirtualDOMNode` implements

## 8. Tests

- [ ] 8.1 Write tests for `VirtualDOMNode` — tree construction, attribute operations, event listener recording, dispatchEvent
- [ ] 8.2 Write tests for `ServerDOMPort.render_html()` — element serialization, void tags, attribute escaping, text escaping, nested trees
- [ ] 8.3 Write tests for unified render path — render the same component tree in both browser mock and server DOMPort, verify identical structure
- [ ] 8.4 Update existing SSG tests — migrate from HTML string comparison to virtual tree structure inspection where beneficial; keep string comparison as integration tests
- [ ] 8.5 Write tests for server-side rendering of components with attributes, event handlers, conditional branches, and list rendering
- [ ] 8.6 Run existing test suite and fix regressions

## 9. Cleanup

- [ ] 9.1 Search codebase for any remaining `_render_html` references — ensure all are removed or migrated
- [ ] 9.2 Remove any `_render_html`-specific test utilities or helpers
- [ ] 9.3 Update type stubs if `_render_html` appears in any `.pyi` files

## 10. Verification

- [ ] 10.1 Run lint: `uv run ruff check .`
- [ ] 10.2 Run type check: `uv run pyright`
- [ ] 10.3 Run unit tests: `uv run python -m pytest tests/ --tb=short`
- [ ] 10.4 Run SSG and verify output: `uv run python -m webcompy generate --app docs_app.bootstrap:app`
- [ ] 10.5 Diff generated docs against baseline to confirm no output regressions
- [ ] 10.6 Verify dev server starts: `uv run python -m webcompy start --dev --app docs_app.bootstrap:app`
