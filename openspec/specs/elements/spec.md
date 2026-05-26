# Elements (Virtual DOM)

## Purpose

The element system is how WebComPy represents and manipulates the user interface. Rather than requiring developers to write HTML templates or JSX, WebComPy provides a Python API for constructing element trees — each element corresponds to a DOM node, and signal values can be used directly as attributes, text content, or list sources.

The system does not use virtual DOM diffing. Instead, it takes a direct approach: when a reactive value changes, the specific DOM node that depends on that value is updated in place. For dynamic content (conditional rendering and list rendering), the entire subtree is regenerated when the controlling value changes. This trades fine-grained efficiency for implementation simplicity.

**What WebComPy does not yet provide:** WebComPy's `repeat` now supports key-based reconciliation and dict-based rendering for efficient DOM updates. Conditional branches (`switch`) reuse DOM nodes when branches share structure via patching, but complete subtree replacement still occurs when branch structures differ entirely.

## Requirements

### Requirement: Rendering shall use a single unified code path in both environments

All element types SHALL use the same `render()` → `_get_node()` → `_init_node()` → `_create_node()` call chain regardless of environment. On the browser, `_create_node()` SHALL delegate to `BrowserDOMPort.create_element()` which returns a `BrowserDOMNode`. On the server, `_create_node()` SHALL delegate to `ServerDOMPort.create_element()` which returns a `VirtualDOMNode`. All subsequent operations (attribute setting, child appending, event listener registration) SHALL work identically through the `DOMNode` Protocol on both implementations.

#### Scenario: Rendering a div in the browser
- **WHEN** `element.render()` is called in the browser
- **THEN** `_create_node()` SHALL call `BrowserDOMPort.create_element("div")`
- **AND** return a `BrowserDOMNode` wrapping a real JS DOM element
- **AND** `_init_new_node()` SHALL set attributes and event listeners on the returned node

#### Scenario: Rendering a div on the server
- **WHEN** `element.render()` is called on the server
- **THEN** `_create_node()` SHALL call `ServerDOMPort.create_element("div")`
- **AND** return a `VirtualDOMNode` with `nodeName == "DIV"`
- **AND** `_init_new_node()` SHALL set attributes and event listeners on the returned node
- **AND** no exception SHALL be raised

### Requirement: AppDocumentRoot._init_node() shall work in both environments

`AppDocumentRoot._init_node()` SHALL create a `DOMNode` in both browser and server environments. In the browser, it SHALL query the existing DOM via `DOMPort.query_selector()` for hydration. On the server, it SHALL create a `VirtualDOMNode` via `DOMPort.create_element()` with the mount element's tag and `id` attribute. No exception SHALL be raised in either environment.

#### Scenario: Server-side AppDocumentRoot creates a virtual mount node
- **WHEN** `AppDocumentRoot._init_node()` is called on the server
- **THEN** a `VirtualDOMNode` SHALL be returned with the mount element's tag name
- **AND** the node SHALL have an `id` attribute matching the selector
- **AND** `__webcompy_node__` SHALL be `True`
- **AND** no exception SHALL be raised

#### Scenario: Browser-side AppDocumentRoot queries existing DOM
- **WHEN** `AppDocumentRoot._init_node()` is called in the browser
- **THEN** `DOMPort.query_selector(selector)` SHALL be called to find the mount element
- **AND** prerendered attributes SHALL be cleaned up as before
- **AND** hydration SHALL proceed as before

### Requirement: Signal values in elements shall update the DOM automatically
When a signal value is used as an element attribute or text content, any change to that value SHALL automatically update the corresponding DOM node without manual intervention.

#### Scenario: Using a signal attribute
- **WHEN** a developer writes `html.INPUT({"value": my_reactive_text})`
- **AND** later sets `my_reactive_text.value = "new text"`
- **THEN** the input element's `value` attribute SHALL update in the DOM

#### Scenario: Using signal text content
- **WHEN** a developer writes `TextElement(my_count)` where `my_count` is a `Signal`
- **AND** later increments `my_count`
- **THEN** the text content in the DOM SHALL update to reflect the new count

### Requirement: Conditional rendering shall display one branch at a time
The `switch` construct SHALL evaluate a series of conditions and render the template of the first matching condition. When conditions change, the previous branch SHALL be removed and the new branch SHALL be rendered. The branch template MAY return a `DynamicElement` (such as a `repeat`), and the `SwitchElement` SHALL handle it as a transparent child with no DOM node of its own. When the `SwitchElement` is refreshed due to a signal change (such as a route change), any `on_after_rendering` lifecycle hooks of newly created components SHALL be deferred until after the reactive propagation and DOM updates have completed.

#### Scenario: Switching between display modes
- **WHEN** a developer defines `switch(cases=[(is_admin, lambda: AdminPanel()), (is_user, lambda: UserPanel())], default=lambda: GuestPanel())`
- **AND** `is_admin` becomes `True`
- **THEN** `AdminPanel` SHALL be rendered
- **WHEN** `is_admin` becomes `False` and `is_user` becomes `True`
- **THEN** `AdminPanel` SHALL be removed and `UserPanel` SHALL be rendered

#### Scenario: Switching routes triggers async operations in new component
- **WHEN** a `SwitchElement` is used for routing (as in `RouterView`)
- **AND** the route changes from one page to another
- **AND** the new page component has an `on_after_rendering` hook that starts async operations
- **THEN** the new component SHALL be fully mounted in the DOM before `on_after_rendering` runs
- **AND** async operations SHALL execute in a clean event loop context (not nested within the signal callback chain)

#### Scenario: Switch branch containing a repeat element
- **WHEN** a developer defines `switch(cases=[(is_list_view, lambda: repeat(items, item_template))])`
- **AND** `is_list_view` becomes `True`
- **THEN** the `repeat` SHALL render its items inside the switch's parent DOM node
- **WHEN** `is_list_view` becomes `False`
- **THEN** the `repeat` and all its rendered items SHALL be removed

### Requirement: List and dict rendering shall map signal collections to element templates with type-safe overloads
The `repeat` construct SHALL support five type-safe overload signatures:

1. `repeat(ReactiveDict[K, V], template: (V,) -> ChildNode)` — dict value-only, keyed by dict keys
2. `repeat(ReactiveDict[K, V], template: (V, K) -> ChildNode)` — dict value+key, keyed by dict keys
3. `repeat(ReactiveList[V], template: (V,) -> ChildNode)` — list unkeyed (backward compatible, full rebuild)
4. `repeat(ReactiveList[V], template: (V, int) -> ChildNode)` — list with index as key
5. `repeat(ReactiveList[V], template: (V, K) -> ChildNode), key: (V) -> K)` — list with custom key function

When `key` is provided (overloads 2, 4, 5) or dict mode is used (overloads 1, 2), `RepeatElement` SHALL reuse existing DOM elements for items whose keys persist across mutations. When no `key` is provided and single-arg template is used (overload 3), all rendered items SHALL be removed and regenerated (full rebuild behavior).

#### Scenario: Rendering a list of items with key function
- **WHEN** a developer writes `repeat(items, lambda item, id: html.LI({"data-id": id}, item.name), key=lambda item: item.id)`
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** only the new `<li>` SHALL be created and appended
- **AND** existing `<li>` elements SHALL remain in the DOM unchanged

#### Scenario: Rendering a list of items without keys (backward compatible)
- **WHEN** a developer writes `repeat(items, lambda item: html.LI({}, item.name))` without a `key` parameter
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** the entire list SHALL be regenerated with the new item included

#### Scenario: Rendering a ReactiveDict with value-only template
- **WHEN** a developer writes `repeat(my_dict, lambda value: html.LI({}, value))`
- **THEN** one `<li>` SHALL be rendered for each value in `my_dict`
- **AND** dict keys SHALL be used as reconciliation identifiers for efficient DOM updates

#### Scenario: Rendering a ReactiveDict with value-key template
- **WHEN** a developer writes `repeat(my_dict, lambda value, key: html.LI({}, f"{key}: {value}"))`
- **THEN** one `<li>` SHALL be rendered for each key-value pair in `my_dict`
- **AND** dict keys SHALL be used as reconciliation identifiers for efficient DOM updates

### Requirement: Pre-rendered DOM nodes shall be reused during hydration via adopt-and-hydrate
When full hydration is enabled, elements SHALL use `_hydrate_node()` instead of `_init_node()` for prerendered nodes. `_hydrate_node()` SHALL check for an existing prerendered node and delegate to `_adopt_node()` if found, or fall back to `_init_node()` if not. This enables efficient hydration of server-rendered content. This requirement applies to all node types including `#text` nodes. During hydration, attribute values and text content SHALL only be written if they differ from the prerendered values to avoid redundant DOM operations.

#### Scenario: Hydrating an existing prerendered element
- **WHEN** `_hydrate_node()` is called and a prerendered node with matching tag exists
- **THEN** `_adopt_node(node)` SHALL be called to adopt the existing DOM node
- **AND** the framework SHALL NOT call `_mount_node()` since the node is already in the DOM

#### Scenario: No prerendered node available during hydration
- **WHEN** `_hydrate_node()` is called and no prerendered node exists
- **THEN** the element SHALL fall back to `_init_node()` for normal DOM creation and mounting

#### Scenario: Hydrating a server-rendered page
- **WHEN** the browser finds an existing DOM node with `__webcompy_prerendered_node__ = True` and a matching tag name
- **THEN** the element SHALL adopt that node rather than creating a new one
- **AND** attributes SHALL be updated to match the element's current state
- **AND** attributes whose values already match SHALL NOT be rewritten to the DOM

#### Scenario: Hydrating an element with identical attributes
- **WHEN** a prerendered element node's attribute values match the Element's current attribute state
- **THEN** the framework SHALL NOT call `setAttribute` for matching attributes
- **AND** attributes with value resolved to `None` in the component state SHALL still be removed via `removeAttribute` if present on the node

#### Scenario: Hydrating an element with differing attributes
- **WHEN** a prerendered element node's attribute differs from the Element's current state
- **THEN** the framework SHALL call `setAttribute` only for the differing attributes
- **AND** matching attributes SHALL remain untouched

#### Scenario: Hydrating a server-rendered text node
- **WHEN** the browser finds an existing `#text` node with `__webcompy_prerendered_node__ = True`
- **THEN** the TextElement SHALL adopt that node rather than removing it and creating a new one
- **AND** if the node's `textContent` matches the element's current value, no DOM write SHALL occur
- **AND** if the node's `textContent` differs, it SHALL be updated to the element's current value
- **AND** no visible flash SHALL occur during hydration

#### Scenario: Hydrating a reactive text node
- **WHEN** a TextElement wraps a Signal value
- **AND** the browser finds a pre-rendered `#text` node for it
- **THEN** the TextElement SHALL adopt the existing node and update its content to the Signal's current value
- **AND** subsequent Signal changes SHALL update the adopted node via the existing `on_after_updating` callback

### Requirement: ElementBase._adopt_node() shall adopt an existing DOM node
`ElementBase._adopt_node(node)` SHALL adopt an existing DOM node by setting `_node_cache` and `_mounted=True`, setting `node.__webcompy_node__ = True`, removing stale attributes (present on node but not in current attrs), setting matching attributes with equality check, registering Signal callbacks for reactive attributes, attaching event handlers, and initializing `DomNodeRef` if present. It SHALL NOT call `_mount_node()`.

#### Scenario: Adopting a prerendered div element
- **WHEN** `_adopt_node(node)` is called on an existing `<div>` DOM node
- **THEN** the element SHALL set `_node_cache` and `_mounted=True`
- **AND** stale attributes SHALL be removed and matching attributes SHALL be set
- **AND** Signal callbacks and event handlers SHALL be registered
- **AND** `_mount_node()` SHALL NOT be called

### Requirement: TextElement._adopt_node() shall adopt an existing text node
`TextElement._adopt_node(node)` SHALL adopt an existing text node by setting `_node_cache` and `_mounted=True`, and conditionally updating `textContent` if it differs.

#### Scenario: Adopting a prerendered text node with matching content
- **WHEN** `_adopt_node(node)` is called on an existing `#text` node with matching content
- **THEN** the text node SHALL be adopted without updating `textContent`
- **AND** `_node_cache` and `_mounted=True` SHALL be set

#### Scenario: Adopting a prerendered text node with differing content
- **WHEN** `_adopt_node(node)` is called on an existing `#text` node with different content
- **THEN** `textContent` SHALL be updated to the element's current value
- **AND** `_node_cache` and `_mounted=True` SHALL be set

### Requirement: ElementBase._detach_from_node() shall release Python-side resources
`ElementBase._detach_from_node()` SHALL release Python-side resources (event handler proxies via `destroy()`, Signal callbacks, DomNodeRef) without removing the DOM node. It SHALL be called when an old element's DOM node is adopted by a new element.

#### Scenario: Detaching from an adopted DOM node
- **WHEN** an old element's DOM node is adopted by a new element during patching
- **THEN** `_detach_from_node()` SHALL destroy event handler proxies, remove Signal callbacks, and clear DomNodeRef
- **AND** the DOM node itself SHALL NOT be removed from the document

### Requirement: _patch_children() and _is_patchable() shall support node reuse across conditional branches
`_patch_children(old_children, new_children)` SHALL recursively compare old and new element lists by tag name, adopting matching DOM nodes and cleaning up unmatched old elements. Matched old elements are detached via `_detach_from_node()`; unmatched old elements are removed via `_remove_element()`. When repositioning nodes within the parent DOM, the DynamicElement's `_node_idx` SHALL be added as an offset so that children are placed at the correct global DOM position (accounting for any preceding sibling DOM nodes).

`_is_patchable(old, new)` SHALL return `True` when two elements share the same tag name (for `ElementBase`) or are both `TextElement` instances. `DynamicElement` pairs are never patchable. `Component` pairs are patchable when their root tag names match.

#### Scenario: Patching children with matching tag names
- **WHEN** `_patch_children()` compares old and new children with matching tag names
- **THEN** matching old elements SHALL be detached via `_detach_from_node()` and their nodes adopted by new elements
- **AND** only unadopted new children SHALL call `_render()`

#### Scenario: Patching children with unmatched elements
- **WHEN** `_patch_children()` finds old elements with no matching new element
- **THEN** unmatched old elements SHALL be removed via `_remove_element()`

#### Scenario: Checking patchability of two elements
- **WHEN** `_is_patchable(old, new)` is called on two `ElementBase` instances with the same tag name
- **THEN** it SHALL return `True`
- **WHEN** `_is_patchable(old, new)` is called on a `DynamicElement` pair
- **THEN** it SHALL return `False`

#### Scenario: Repositioning children when DynamicElement has preceding siblings
- **WHEN** `_patch_children()` is called on a DynamicElement whose `_node_idx` is greater than 0 (i.e., there are sibling DOM nodes before the DynamicElement's content in the parent)
- **AND** a child element is repositioned via `_reposition_node()`
- **THEN** the child SHALL be placed at `DynamicElement._node_idx + local_child_index` in the parent DOM
- **AND** preceding sibling DOM nodes SHALL remain at their original positions

### Requirement: _reposition_node() shall recover detached DOM nodes
When `_reposition_node()` is called on an element whose cached DOM node has been detached from its DOM parent by an external mutation (i.e., `element._node_cache.parentNode` is `null`), the function SHALL resolve the correct parent DOM node from the element tree via `element._parent._get_node()` and reinsert the node at the target index. If `element._parent._get_node()` also fails to return a valid parent, the function SHALL return without error (no-op).

This requirement SHALL NOT apply to `DynamicElement` instances themselves (which have no DOM node of their own).

#### Scenario: Repositioning a text node detached by external code
- **WHEN** a `TextElement`'s cached DOM node has been removed from the DOM by external JavaScript (e.g., highlight.js replacing `innerHTML`)
- **AND** `_reposition_node()` is called on that `TextElement`
- **THEN** the text node SHALL be reinserted into the DOM at the correct position using the parent DOM node obtained from `element._parent._get_node()`
- **AND** if the target index exceeds the parent's child list length, the node SHALL be appended to the end

#### Scenario: Repositioning a node that is already in the DOM
- **WHEN** `_reposition_node()` is called on an element whose cached DOM node still has a valid `parentNode`
- **THEN** the function SHALL use the existing `parentNode` directly (preserving existing behavior)

### Requirement: Conditional rendering shall reuse DOM nodes when branches share structure
When a conditional branch changes, `SwitchElement._refresh()` SHALL use `_patch_children()` to compare old and new children, adopting matching DOM nodes instead of destroying and recreating all children. All children SHALL call `_render()` to ensure lifecycle hooks fire correctly on patched components and unmounted descendants are rendered. The deferred rendering mechanism (`start_defer_after_rendering` / `end_defer_after_rendering`) SHALL be preserved.

#### Scenario: Switching between branches with shared structure
- **WHEN** a `SwitchElement` condition changes from one branch to another
- **AND** the old and new branches share tag names at the same positions
- **THEN** matching DOM nodes SHALL be adopted rather than destroyed and recreated
- **AND** the deferred rendering mechanism SHALL be preserved

#### Scenario: Switching between branches with different structure
- **WHEN** a `SwitchElement` condition changes to a branch with entirely different structure
- **THEN** old elements SHALL be removed via `_remove_element()` and new elements SHALL be created via `_render()`

### Requirement: Event handlers shall propagate user interactions to Python
Developers SHALL be able to attach event handlers to elements using `@event_name` attribute syntax. In the browser, these handlers SHALL be properly proxied for PyScript interop and cleaned up when the element is removed.

#### Scenario: Handling a button click
- **WHEN** a developer writes `html.BUTTON({"@click": on_click}, "Click me")`
- **THEN** clicking the button in the browser SHALL invoke the `on_click` Python function
- **AND** the event handler SHALL receive the DOM event object

### Requirement: DOM references shall allow direct access to real DOM nodes
Developers SHALL be able to create a `DomNodeRef` and pass it as a `:ref` attribute to any element. After the element is rendered, the ref SHALL provide access to the underlying DOM node for imperative operations.

#### Scenario: Focusing an input element
- **WHEN** a developer creates `input_ref = DomNodeRef()` and passes it as `":ref"` on an input element
- **AND** the element is rendered
- **THEN** `input_ref.element` SHALL return the actual DOM input element
- **AND** `input_ref.element.focus()` SHALL focus the input in the browser

### Requirement: _mount_node() shall recover detached nodes when _mounted flag is True

`_mount_node()` SHALL handle four states based on the `_mounted` flag and the node's `parentNode`:

- `_mounted is None`: First-time mount — insert or append the node at `_node_idx`
- `_mounted is False`: Remount after `_detach_node()` — replace the remount placeholder
- `_mounted is True` AND `node.parentNode is not None`: Normal state — skip, node is already in the DOM
- `_mounted is True` AND `node.parentNode is None`: Detached recovery — the node was adopted (via `_adopt_node()`) but subsequently detached from the DOM by external code; SHALL reinsert the node at `_node_idx`

After mounting or remounting, `_mounted` SHALL be set to `True`.

#### Scenario: First-time mount
- **WHEN** `_mount_node()` is called with `_mounted is None`
- **AND** the parent DOM node exists
- **THEN** the node SHALL be inserted into the parent at `_node_idx`
- **AND** `_mounted` SHALL be set to `True`

#### Scenario: Remount after detach_node
- **WHEN** `_mount_node()` is called with `_mounted is False` and `_remount_to` is set
- **THEN** the node SHALL replace `_remount_to` in the parent
- **AND** `_remount_to` SHALL be cleared
- **AND** `_mounted` SHALL be set to `True`

#### Scenario: Skip when already mounted and in DOM
- **WHEN** `_mount_node()` is called with `_mounted is True` and `node.parentNode is not None`
- **THEN** no DOM operations SHALL be performed
- **AND** `_mounted` SHALL remain `True`

#### Scenario: Recover detached node after external DOM mutation
- **WHEN** `_mount_node()` is called with `_mounted is True` and `node.parentNode is None`
- **THEN** the node SHALL be reinserted into the parent at `_node_idx`
- **AND** the node SHALL be appended if `_node_idx` exceeds the parent's child list length
- **AND** `_mounted` SHALL remain `True`

#### Scenario: Detached node recovery does not affect DynamicElement
- **WHEN** a `DynamicElement` subclass has a detached node
- **THEN** the standard `_mount_node()` logic for `_mounted is True` SHALL not interfere with DynamicElement's own rendering path

### Requirement: NewLine._init_node() shall not remove WebComPy-managed DOM nodes

When `NewLine._init_node()` finds an existing DOM node at its expected sibling index and the node's tag does not match `<br>`, it SHALL check whether the node is managed by WebComPy (marked with `__webcompy_node__`). If the node has `__webcompy_node__` set, `_init_node()` SHALL NOT call `existing_node.remove()`, preserving the node for its owning element. This prevents `NewLine` from destroying adopted WebComPy-managed nodes during SPA navigation when `_patch_children()` shifts DOM siblings.

#### Scenario: NewLine preserves adopted WebComPy node during SPA navigation
- **WHEN** `_patch_children()` removes an unmatched old `<br>` node from the parent DOM
- **AND** subsequent sibling indices shift so `NewLine._init_node()` finds a `__webcompy_node__`-marked `<div>` instead of a `<br>`
- **THEN** `NewLine._init_node()` SHALL NOT call `existing_node.remove()`
- **AND** the adopted WebComPy-managed `<div>` SHALL remain in the DOM

#### Scenario: NewLine still removes non-WebComPy nodes
- **WHEN** `NewLine._init_node()` finds an existing DOM node without `__webcompy_node__` at its expected sibling index
- **AND** the node's tag does not match `<br>`
- **THEN** `existing_node.remove()` SHALL be called to clean up the unexpected node