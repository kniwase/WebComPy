## 1. VirtualDOMNode implementation

- [x] 1.1 Create `webcompy/ports/_server/_virtual_dom.py` with `VirtualDOMNode` class satisfying `DOMNode` Protocol — store `tag_name`, `attributes: dict`, `children: list`, `event_listeners: list`, `text_content`, `node_type`, `__webcompy_node__`, `_parent`
- [x] 1.2 Implement tree operations: `appendChild`, `removeChild`, `insertBefore`, `replaceChild`, `remove` — manage children list and parent references
- [x] 1.3 Implement attribute operations: `setAttribute`, `getAttribute`, `removeAttribute`, `hasAttribute`, `getAttributeNames`
- [x] 1.4 Implement event operations: `addEventListener`, `removeEventListener` — store as `(event_name, handler)` tuples
- [x] 1.5 Create `VirtualDOMEvent` class in `webcompy/ports/_server/_virtual_dom.py` satisfying the `DOMEvent` Protocol — full fields: `type`, `bubbles`, `cancelable`, `target`, `currentTarget`, `defaultPrevented`, `eventPhase`, `timeStamp`, `preventDefault()` (gates on `cancelable`), `stopPropagation()`
- [x] 1.6 Implement `dispatchEvent(event: DOMEvent) -> bool` on `VirtualDOMNode` — at-target phase (eventPhase=2, target=currentTarget=this), then bubbling phase (eventPhase=3, walk _parent chain) if `event.bubbles`. Stop if `event._propagation_stopped`. Return `not event.defaultPrevented`. The capturing phase SHALL NOT be implemented (WebComPy always uses `useCapture=False`).
- [x] 1.7 Implement properties: `childNodes` (returns list), `textContent` (get/set), `nodeName` (returns tag_name), `nodeType` (1=element, 3=text)

## 2. Protocol layer — DOMEvent, DOMNode, DOMPort

- [x] 2.1 Move `DOMEvent` Protocol from `webcompy/elements/_dom_objs.py` to `webcompy/ports/_dom.py` — alongside `DOMNode` and `DOMPort`. Keep re-export in `_dom_objs.py` for backwards compatibility.
- [x] 2.2 Add `dispatchEvent(event: DOMEvent) -> bool` to `DOMNode` Protocol in `webcompy/ports/_dom.py`
- [x] 2.3 Add `create_event(event_type: str, *, bubbles: bool = False, cancelable: bool = False) -> DOMEvent` abstract method to `DOMPort` ABC in `webcompy/ports/_dom.py`
- [x] 2.4 Implement `BrowserDOMPort.create_event()` — create a native JS `Event` via `new Event(type, {bubbles, cancelable})` or equivalent browser API
- [x] 2.5 Implement `ServerDOMPort.create_event()` — return a `VirtualDOMEvent(type, bubbles=bubbles, cancelable=cancelable)`

## 3. ServerDOMPort rewrite

- [x] 3.1 Rewrite `webcompy/ports/_server/_dom.py` — replace exception-throwing stubs with virtual DOM factory: `create_element()` returns `VirtualDOMNode`, `create_text_node()` returns virtual text node
- [x] 3.2 Implement `ServerDOMPort.render_html(node: DOMNode) -> str` — traverse virtual tree, serialize to HTML string
- [x] 3.3 Implement HTML serialization rules: HTML-escape text content and attribute values, output void elements without closing tags (e.g., `<br>`, `<img>`) per HTML5 convention, omit `None`-valued attributes
- [x] 3.4 Verify `render_html()` produces identical output to current `_render_html()` methods — generate docs_app with both paths and diff results

## 4. Unify render path in element base classes

- [x] 4.1 Remove `_render_html()` abstract method from `ElementAbstract` in `webcompy/elements/types/_abstract.py` — after cli/_html.py is migrated (task 7)
- [x] 4.2 Remove `_render_html()` from `ElementWithChildren` in `webcompy/elements/types/_base.py`
- [x] 4.3 Update `TextElement._update_text()` in `webcompy/elements/types/_text.py` — remove `if browser:` branch; both environments call `node.textContent = new_text` since `VirtualDOMNode` supports it
- [x] 4.4 Remove `if not browser:` server branches from `_on_set_parent()` in element and router types — `_switch.py:84`, `_repeat.py:95`, `_view.py:25` (router). After virtual DOM unification, `render()` creates VirtualDOMNodes on the server via `ServerDOMPort`, so the server-only pre-creation logic inside these branches is no longer needed and would cause double creation
- [x] 4.5 Verify that `_init_node()` (already unbranchified by `feat-port-abstraction`) works correctly with `VirtualDOMNode` on the server — both `ElementBase._init_node()` and `TextElement._init_node()` / `NewLine._init_node()` call `_create_node()` which delegates to `inject(DOM_PORT_KEY)` returning a `VirtualDOMNode`
- [x] 4.6 Verify that `_detach_node()` (already unbranchified by `feat-port-abstraction`) works correctly with `VirtualDOMNode` on the server — `dom_port.create_text_node("")` returns a virtual text node and `parent_node.replaceChild(...)` operates on the virtual children list
- [x] 4.7 Remove `if browser:` branch from `DynamicElement._render()` in `webcompy/elements/types/_dynamic.py` — after virtual DOM unification, `_position_element_nodes()` works on `VirtualDOMNode` (uses `appendChild`/`insertBefore` which `VirtualDOMNode` implements), so both environments use the same positioning logic
- [x] 4.8 Remove environment guard from `RepeatElement._refresh()` in `webcompy/elements/types/_repeat.py:148` — change `if self._has_key and browser and self._children_keys:` to `if self._has_key and self._children_keys:`. After virtual DOM unification, `VirtualDOMNode` implements all DOM operations used by `_reconcile_children()` (`appendChild`, `insertBefore`, `remove`), so key-based reconciliation works identically on the server
- [x] 4.9 Remove environment guard from `_component.py:172` — change `app._defer_depth > 0 and ENVIRONMENT == "pyscript"` to `app._defer_depth > 0`. After virtual DOM unification, both environments run `render()`, and the defer mechanism works correctly on the server via synchronous `schedule_macro_task()`. The guard is an unnecessary optimization that diverges from Decision 3's single-code-path goal

## 5. Router accessibility for testing

- [x] 5.1 Modify `RouterLink._on_click()` in `webcompy/router/_link.py` — remove `ENVIRONMENT != "pyscript"` early return; instead, guard only the `pyscript` import, `pushState`, and `window.location` access inside a `if ENVIRONMENT == "pyscript"` block. `self._router.__set_path__(href, params)` executes unconditionally so that `dispatchEvent(VirtualDOMEvent("click"))` on a rendered RouterLink triggers full route transition (guards → navigate → after_route_change → SwitchElement route selection)

## 6. Remove _render_html() from element subclasses

- [x] 6.1 Remove `_render_html()` from `TextElement` and `NewLine` in `webcompy/elements/types/_text.py`
- [x] 6.2 Remove `_render_html()` from `DynamicElement` in `webcompy/elements/types/_dynamic.py`

## 7. Update server-side rendering entry points

- [x] 7.1 Update SSG generation code to use `ServerDOMPort.render_html(root_node)` instead of calling element `_render_html()` directly
- [x] 7.2 Update `webcompy/cli/_generate.py` if it references `_render_html()`
- [x] 7.3 Update `webcompy/cli/_html.py` if it references `_render_html()`

## 8. Element system adapter for server DOMPort

- [x] 8.1 Verify `DomNodeRef` is compatible with `VirtualDOMNode` — `DomNodeRef.__init_node__(node)` sets `self._node = node` and `node` must satisfy `DOMNode` Protocol; `VirtualDOMNode` already does
- [x] 8.2 Verify `ElementBase._init_new_node()` works on `VirtualDOMNode` — `setAttribute` and `addEventListener` use `DOMNode` Protocol which `VirtualDOMNode` implements

## 9. Tests

- [x] 9.1 Write tests for `VirtualDOMNode` — tree construction, attribute operations, event listener recording, dispatchEvent (including bubbling, stopPropagation, preventDefault)
- [x] 9.2 Write tests for `ServerDOMPort.render_html()` — element serialization, void tags, attribute escaping, text escaping, nested trees
- [x] 9.3 Write tests for unified render path — render the same component tree in both browser mock and server DOMPort, verify identical structure
- [x] 9.4 Update existing SSG tests — migrate from HTML string comparison to virtual tree structure inspection where beneficial; keep string comparison as integration tests
- [x] 9.5 Write tests for server-side rendering of components with attributes, event handlers, conditional branches, and list rendering
- [x] 9.6 Run existing test suite and fix regressions

## 10. Cleanup

- [x] 10.1 Search codebase for any remaining `_render_html` references — ensure all are removed or migrated
- [x] 10.2 Remove any `_render_html`-specific test utilities or helpers
- [x] 10.3 Update type stubs if `_render_html` appears in any `.pyi` files

## 11. Verification

- [x] 11.1 Run lint: `uv run ruff check .`
- [x] 11.2 Run type check: `uv run pyright`
- [x] 11.3 Run unit tests: `uv run python -m pytest tests/ --tb=short`
- [x] 11.4 Run SSG and verify output: `uv run python -m webcompy generate --app docs_app.bootstrap:app`
- [x] 11.5 Diff generated docs against baseline to confirm no output regressions
- [x] 11.6 Verify dev server starts: `uv run python -m webcompy start --dev --app docs_app.bootstrap:app`
