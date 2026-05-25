## Context

### Current State

WebComPy's `ElementWithChildren._render()` unconditionally removes any child DOM nodes that exceed `_children_length` after rendering:

```python
# webcompy/elements/types/_base.py lines 39-41
if (node := self._get_node()) is not None:
    for _ in range(node.childNodes.length - self._children_length):
        node.childNodes[-1].remove()
```

This assumes exclusive ownership of all `childNodes`. The same cleanup exists in `_hydrate_node()`. When external JavaScript (e.g., highlight.js) injects child nodes into WebComPy-managed elements, they are destroyed on the next render.

Additionally, `_mount_node()` has a gap: when `_mounted` is `True`, it skips entirely — even if the cached DOM node has been detached from its parent by external code. This happens when `_patch_children()` adopts a node via `_adopt_node()` (which sets `_mounted=True`), but that node was already removed from the DOM by external JavaScript.

### Root Cause Chain

During a RouterLink transition (HelloWorldPage → FizzbuzzPage):

```
SwitchElement._refresh()
  → _patch_children(HelloWorldPage, FizzbuzzPage)
    → Component patches match (both DIV.container)
    → Recursive patch: DemoDisplay → ... → PRE → CODE → TextElement all match
    → TextElement._adopt_node(old_text_node)
      → _mounted = True, but old_text_node was already removed by hljs
    → TextElement._render() → _mount_node()
      → _mounted is True → SKIP (text node never reinserted)
  → ElementWithChildren._render() on CODE
    → childNodes.length (hljs spans) - _children_length (1) = N-1
    → removes all hljs spans
  → CODE is empty, text node is dangling
```

### Related Changes

- **PR #148** (fix-node-index-confusion): `_patch_children` passes `node_idx_offset` to `_reposition_node` — merged
- **PR #149** (fix-reposition-detached-node): `_reposition_node` recovers detached nodes via `element._parent._get_node()` — merged
- These fix index misplacement but do not address the cleanup loop or the mount skip

## Goals / Non-Goals

**Goals:**
- Allow elements to declare that external JavaScript may manage their child DOM nodes
- Skip the excess-child-node cleanup loop for elements with `:preserve_children`
- Reinsert detached nodes during `_mount_node()` when `_mounted is True` but node is detached
- Follow the existing `:ref` / `DomNodeRefKey` pattern for consistency
- Enable docs_app components (DemoDisplay, SyntaxHighlighting) to use hljs without DOM corruption
- Support VDOM-based unit testing of all three scenarios

**Non-Goals:**
- A general-purpose shadow DOM or isolation zone mechanism
- Framework-level integration with specific external libraries
- Runtime API for marking regions as externally-managed after render
- Changing the `_is_patchable` logic or reconciliation algorithm
- Supporting `:preserve_children` on `DynamicElement` types (SwitchElement, RepeatElement)

## Decisions

### Decision 1: `_mount_node()` detached-node recovery

**Choice**: Add an `elif` branch to `_mount_node()` that re-inserts the node when `_mounted is True` but `node.parentNode is None`.

```python
elif self._mounted and (node := self._get_node()) and node.parentNode is None:
    parent_node = self._parent._get_node()
    if parent_node.childNodes.length <= self._node_idx:
        parent_node.appendChild(node)
    else:
        next_node = parent_node.childNodes[self._node_idx]
        parent_node.insertBefore(node, next_node)
```

**Rationale**: This handles the case where `_adopt_node()` set `_mounted=True` but the adopted node was later detached from the DOM (by `innerHTML` replacement, `removeChild`, etc.). The condition is strict enough to avoid affecting normal operation: in normal flow, `_mounted` is only `True` when the node IS in the DOM.

**Alternatives considered:**
- Reset `_mounted = None` in `_adopt_node()` instead: would break hydration semantics (node IS in DOM after adopt in normal hydration)
- Call `_mount_node()` unconditionally: would cause unnecessary DOM operations on every re-render

| State | `_mounted` | `parentNode` | Before | After |
|-------|-----------|-------------|--------|-------|
| Initial render | `None` | N/A | Mount | Mount |
| Remount after detach | `False` | N/A | Remount | Remount |
| Normal, node in DOM | `True` | not None | Skip | Skip |
| Adopted but detached | `True` | **None** | **Skip (bug)** | **Reinsert** |

**Interaction with `DynamicElement._render()` and `_position_element_nodes()`**: The `_mount_node()` recovery path uses the same re-insertion logic (insertBefore/appendChild based on `_node_idx`) as the first-time mount path. For `DynamicElement` children, `DynamicElement._render()` additionally calls `_position_element_nodes()` after rendering children, which iterates all descendants and positions them. The `_mount_node()` recovery runs first (during `child._render()`), putting the node in the correct position. `_position_element_nodes()` runs afterward, finding the node already at the correct position (`ref_node is not node` → `False`), and becomes a no-op. No conflict.

### Decision 2: `:preserve_children` as a special attribute

**Choice**: Introduce a boolean attribute `:preserve_children` that follows the same pattern as `:ref` (extracted in `create_element()`, stored on the element, never rendered as a DOM attribute).

```python
# generators.py
PreserveChildrenKey = NewType("PreserveChildrenKey", str)
preserve_children = PreserveChildrenKey(":preserve_children")

def create_element(tag_name, attributes, *children) -> Element:
    preserve = False
    for name, value in attributes.items():
        if isinstance(value, bool) and name == ":preserve_children":
            preserve = value
    return Element(tag_name, attrs, events, ref, preserve, children)
```

**Rationale**: The `:ref` / `DomNodeRefKey` pattern is well-established and understood in the codebase. Using the same mechanism for `:preserve_children` minimizes surprise. The `:` prefix convention signals that this is a framework-level attribute, not a real DOM attribute.

**Alternatives considered:**
- A real HTML attribute like `data-webcompy-preserve-children`: leaks framework internals into the DOM
- A method call like `element.enable_preserve_children()`: inconsistent with the declarative `:ref` pattern
- A separate `PreservedChildrenElement` subclass: adds complexity without benefit

### Decision 3: Guard in `_render()` and `_hydrate_node()`

**Choice**: Skip the cleanup loop when `_preserve_children is True`:

```python
# _base.py _render()
if (node := self._get_node()) is not None and not self._preserve_children:
    for _ in range(node.childNodes.length - self._children_length):
        node.childNodes[-1].remove()
```

Same guard in `_hydrate_node()`.

**Rationale**: Simple, localized change. The guard is checked at the element level — if a parent has `_preserve_children=True`, child elements still run their own cleanup normally unless they also set the flag. This allows fine-grained control (e.g., only the `<code>` element preserves children, not the entire card).

### Decision 4: Thread through Component

**Choice**: `Component.__init_component()` copies `_preserve_children` from the root `Element` node, just as it already copies `_tag_name`, `_ref`, etc.

```python
self._preserve_children = node._preserve_children
```

**Rationale**: Components wrap a single root `Element`. Since `Component` extends `ElementBase`, it needs to carry the flag to ensure the cleanup guard works. This matches the existing pattern for `_ref`.

### Decision 5: SyntaxHighlighting component enhancement

**Choice**: Enhance the `SyntaxHighlighting` component to accept `SignalBase[str]` in addition to `str` for the `code` prop, add input validation, and switch to `hljs.highlight()` + `innerHTML`.

```python
class SyntaxHighlightingProps(TypedDict):
    code: str | SignalBase[str]
    lang: str

@define_component
def SyntaxHighlighting(context: ComponentContext[SyntaxHighlightingProps]):
    code = context.props["code"]
    code_ref = DomNodeRef()
    get_hljs = inject(HOST_PORT_KEY).create_js_global_getter("hljs")

    def _get_source() -> str:
        return code.value if isinstance(code, SignalBase) else code

    def run_highlight():
        source = _get_source()
        source = _validate_code(source)
        if not source.strip():
            return
        hljs = get_hljs()
        if hljs is not None and code_ref.element:
            result = hljs.highlight(source, {"language": context.props["lang"]})
            code_ref.element.innerHTML = result.value

    if isinstance(code, SignalBase):
        code.on_after_updating(lambda _: run_highlight())

    @context.on_after_rendering
    def _():
        run_highlight()

    return html.PRE(
        {},
        html.CODE(
            {
                "class": f"language-{context.props['lang']}",
                ":ref": code_ref,
                ":preserve_children": True,
            },
        ),
    )
```

Key design points:
- **No `TextElement` child**: The `<code>` element has no WebComPy-managed children, so `_children_length = 0`. Combined with `:preserve_children`, the cleanup loop is skipped entirely.
- **`SignalBase` branching**: `isinstance(code, SignalBase)` check determines whether to wire `on_after_updating` for reactive re-highlighting or run once on render.
- **`hljs.highlight()` + `innerHTML`**: Replaces `hljs.highlightElement()` which mutates the DOM in-place. `hljs.highlight()` returns a `{value, language, ...}` result object; `value` is an HTML-safe string with hljs's own `escapeHTML()` applied.
- **Backward compatible**: Existing call sites in `home.py` pass `str` values — no change needed.

### Decision 6: DemoDisplay simplification

**Choice**: Remove all hljs-related logic from `DemoDisplay` and delegate code rendering to `SyntaxHighlighting`.

```python
# Before: DemoDisplay manages code_ref, get_hljs, source_code, run_highlight
# After:
SyntaxHighlighting({"code": source_code, "lang": "python"})
```

**Rationale**: `DemoDisplay` was duplicating ~80% of `SyntaxHighlighting`'s logic. By passing the `source_code` Signal directly to `SyntaxHighlighting`, we eliminate the duplication. `DemoDisplay` retains only async loading (`load()`) and the iframe markup — the code card is entirely delegated.

### Decision 7: Input validation

**Choice**: Apply lightweight input validation in `_validate_code()` — size limit and null-byte detection only. Do NOT html-escape input (that would break hljs tokenization). Do NOT use DOMParser for output verification (hljs applies its own `escapeHTML()` internally, which is battle-tested).

```python
_MAX_CODE_LENGTH = 100_000

def _validate_code(text: str) -> str:
    if not isinstance(text, str):
        return ""
    if not text.strip():
        return text
    if len(text) > _MAX_CODE_LENGTH:
        return "[Error: code too large]"
    if "\x00" in text:
        return "[Error: invalid characters]"
    return text
```

**Rationale**: hljs applies `escapeHTML()` to all text content before wrapping in `<span>` elements. This means the output HTML is safe by construction — no `<script>` or other dangerous tags can appear inline. Input-side sanitization is limited to structural validation (size, encoding) because Python's `html.escape()` would corrupt the source text that hljs needs to parse as code syntax. Output-side DOMParser verification is unnecessary overhead.

**Alternatives considered:**
- `html.escape()` before hljs: breaks hljs tokenization (e.g., `<div>` becomes `&lt;div&gt;` and hljs can't recognize it as a tag name)
- DOMParser output verification: adds per-render cost, hljs's own encoding makes it redundant
- No validation at all: risk of degenerate inputs (huge strings, binary data) causing rendering issues

## Risks / Trade-offs

- **[Risk] `:preserve_children` on an element blocks ALL child cleanup**: If the developer later adds WebComPy-managed children alongside externally-managed ones, the cleanup loop won't run. Developers must ensure all children of a `:preserve_children` element are externally-managed.
  - **Mitigation**: Document this clearly. This is a power-user feature for specific scenarios (code highlighting, rich text editors, etc.).

- **[Risk] Detached-node recovery could mask bugs**: If a node is detached for a legitimate reason (e.g., it was intentionally removed), re-insertion might cause unexpected behavior.
  - **Mitigation**: The condition is narrow — only triggers when `_mounted is True` AND `parentNode is None`. Legitimate detachment paths (`_detach_node()`, `_detach_from_node()`) set `_mounted=False` or `_mounted=None` respectively, so they won't trigger this path.

- **[Risk] VDOM tests may diverge from real browser behavior**: `VirtualDOMNode` implements `remove()`, `appendChild()`, `parentNode` etc., but subtle differences in event timing or DOM property behavior could exist.
  - **Mitigation**: The VDOM port is already well-tested and used across the test suite. The scenarios being tested (node detachment, child node injection) are structural, not timing-dependent.

## Open Questions

- None currently. All design decisions are settled based on codebase exploration.
