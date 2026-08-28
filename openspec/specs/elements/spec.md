# Elements (Virtual DOM)

## Purpose

The element system is how WebComPy represents and manipulates the user interface. Rather than requiring developers to write HTML templates or JSX, WebComPy provides a Python API for constructing element trees — each element corresponds to a DOM node, and signal values can be used directly as attributes, text content, or list sources.

The system does not use virtual DOM diffing. Instead, it takes a direct approach: when a reactive value changes, the specific DOM node that depends on that value is updated in place. For dynamic content (conditional rendering and list rendering), the entire subtree is regenerated when the controlling value changes. This trades fine-grained efficiency for implementation simplicity.

**What WebComPy does not yet provide:** WebComPy's `repeat` now supports key-based reconciliation and dict-based rendering for efficient DOM updates. Conditional branches (`switch`) reuse DOM nodes when branches share structure via patching, but complete subtree replacement still occurs when branch structures differ entirely.

`Suspense` is a `DynamicElement` (like `SwitchElement` and `RepeatElement`) that provides a declarative async boundary. It shows fallback content while children are loading and swaps to real content on completion. See the `suspense` spec for details.

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

### Requirement: Child node type alias shall accept all renderable node types

`ElementChildren` SHALL be defined as `ElementAbstract | SignalBase[Any] | str | None` in `webcompy/elements/typealias/_element_property.py`. It SHALL be the single child-node type alias used by `NodeGenerator`, `repeat()` templates, and element children. Because `ElementAbstract` is the common root of `Element`, `Component`, `TextElement`, `NewLine`, and all `DynamicElement` subclasses (`SwitchElement`, `RepeatElement`, `MultiLineTextElement`, and future `FragmentElement`), the alias SHALL accept any renderable element node without per-type enumeration. `webcompy/elements/generators.py` SHALL use `ElementChildren` directly for template return types and SHALL NOT maintain a separate alias.

#### Scenario: switch() result is a valid child node
- **WHEN** a `NodeGenerator` returns a `SwitchElement` (from `switch()`)
- **THEN** the return value SHALL be valid as `ElementChildren` under static type checking

#### Scenario: repeat() result is a valid child node
- **WHEN** a `NodeGenerator` returns a `RepeatElement` or `MultiLineTextElement`
- **THEN** the return value SHALL be valid as `ElementChildren` under static type checking

#### Scenario: Future DynamicElement types are automatically covered
- **WHEN** a new `DynamicElement` subclass (e.g., `FragmentElement`) is introduced
- **THEN** it SHALL be automatically valid as `ElementChildren` without requiring an edit to the type alias

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

1. `repeat(ReactiveDict[K, V], template: (V,) -> ElementChildren)` — dict value-only, keyed by dict keys
2. `repeat(ReactiveDict[K, V], template: (V, K) -> ElementChildren)` — dict value+key, keyed by dict keys
3. `repeat(ReactiveList[V], template: (V,) -> ElementChildren)` — list unkeyed (backward compatible, full rebuild)
4. `repeat(ReactiveList[V], template: (V, int) -> ElementChildren)` — list with index as key
5. `repeat(ReactiveList[V], template: (V, K) -> ElementChildren), key: (V) -> K)` — list with custom key function

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

### Requirement: Dynamic containers shall assign child node indices by cumulative node offset

When a container element assigns `_node_idx` to its children during render, refresh, reconciliation, or hydration, each child's index SHALL be the container's own `_node_idx` plus the sum of all preceding siblings' `_node_count` (cumulative node offset). Containers SHALL NOT use the child's enumerate position in the children list as the node offset. This applies to `ElementWithChildren._render`, `DynamicElement._render`, `RepeatElement._refresh` (full-rebuild path), `RepeatElement._reconcile_children`, `SwitchElement._render`, `SwitchElement._refresh`, `SuspenseElement`, `ClientOnlyElement`, and `MarkdownForElement` (`template/_markdown_for.py`), matching the existing cumulative behavior of `_re_index_children`, `_hydrate_node`, `_position_element_nodes`, and `_append_child`. For children with `_node_count == 1` the two schemes coincide; multi-node children (`FragmentElement`) MUST be positioned at non-overlapping offsets.

#### Scenario: Multi-line template for-loop renders all items on initial render
- **WHEN** a template contains `{% for item in items %}` with a multi-line body (whitespace producing `TextElement` siblings, i.e., `FragmentElement` children) over a `ReactiveList`
- **THEN** the initial render SHALL produce one element per item in order, with no item's nodes lost or overlapped

#### Scenario: Multi-line template for-loop keeps all items after list mutation
- **WHEN** a reactive `{% for %}` with a multi-line body has rendered and the underlying `ReactiveList` is mutated (e.g., first item removed)
- **THEN** the refreshed DOM SHALL contain exactly the elements for the updated items in order

#### Scenario: Multi-element if branch toggles without losing nodes
- **WHEN** an `{% if %}` branch contains multiple sibling elements (wrapped in `FragmentElement`) and the condition signal toggles
- **THEN** the outgoing branch's nodes SHALL be removed and the incoming branch's elements SHALL all be present at correct positions

#### Scenario: Keyed reconciliation positions fragment children at non-overlapping offsets
- **WHEN** `repeat` with a `key` function (or `ReactiveDict`) renders templates that produce multi-node children and the collection is mutated
- **THEN** reused and newly created children SHALL be positioned by cumulative node offset with no overlapping `_node_idx` values

#### Scenario: Reactive if branch inside a reactive for-loop survives repeated toggles
- **WHEN** a template contains `{% if %}` (reactive condition) inside `{% for %}` (reactive iterable) and the condition signal toggles more than once while items are also mutated
- **THEN** every toggle SHALL update the DOM without raising and without losing items, and the refreshed DOM SHALL contain exactly the branch elements for all items in order

#### Scenario: Refresh preserves following siblings of a dynamic container
- **WHEN** a dynamic container (e.g., a reactive `{% for %}`) has a following sibling element in its parent and the underlying collection is mutated
- **THEN** the following sibling's DOM node SHALL remain in the parent at its correct position after the refresh, and no node owned by a sibling SHALL be removed or replaced during the container's render or reconcile

#### Scenario: Refresh cancels stale hydration render tasks of replaced children
- **WHEN** hydration has scheduled render tasks for a dynamic container's children and a refresh replaces those children before the tasks execute
- **THEN** no render task scheduled for a replaced child SHALL execute afterwards, and the DOM SHALL contain exactly the current children's nodes (no duplicated nodes from removed children)
- **AND** render tasks scheduled for keyed children that the reconciliation reuses SHALL NOT be cancelled, and SHALL run to completion so each reused child's subtree finishes rendering

### Requirement: Index assignment base SHALL match the container's node ownership

Assigning a child's `_node_idx` SHALL use a base determined by the container's relationship to the DOM: regular (node-owning) containers SHALL index their children from `0` (children occupy the container's own DOM node), and dynamic containers (no own DOM node) SHALL index their children from the container's own `_node_idx` (children occupy the nearest real-DOM-node ancestor's `childNodes`). This applies to `ElementWithChildren._render`, `ElementWithChildren._re_index_children`, and all dynamic-container render/refresh/hydration loops, and SHALL hold across initial render, refresh, keyed reconciliation, and hydration. Consistent with `DynamicElement._hydrate_node` (dynamic: base `self._node_idx`) and `ElementWithChildren._re_index_children`/`_hydrate_node` (regular: base `0`) for their respective kinds.

#### Scenario: Non-zero-offset regular element preserves trailing siblings after refresh
- **WHEN** a regular element whose own `_node_idx` is non-zero contains a dynamic child (e.g., `{% for %}`) followed by static siblings, and the iterable is mutated
- **THEN** the refreshed DOM SHALL keep the static siblings in their original order relative to the dynamic child's nodes

#### Scenario: Dynamic container at non-zero offset repositions children within its parent's node
- **WHEN** a dynamic container whose own `_node_idx` is `k > 0` re-renders or refreshes its children
- **THEN** each child's `_node_idx` SHALL equal `k` plus the cumulative node offset of preceding siblings within the container, and the child's DOM node SHALL be inserted at that index within the nearest real-DOM-node ancestor

### Requirement: `_re_index_children` SHALL be consistent with the receiver's container kind

The `_re_index_children` operation SHALL assign child indices using the same base rule as the container kind of the receiver: base `0` for `ElementWithChildren` (regular) and base `self._node_idx` for `DynamicElement` (dynamic). A refresh path that re-indexes a dynamic parent (e.g., `SwitchElement._refresh`, `MarkdownForElement._refresh`, `RouterView._on_set_parent`) SHALL NOT reset that parent's children to base `0` when the parent sits at a non-zero offset.

#### Scenario: RouterView-style dynamic parent preserves preceding siblings across toggles
- **WHEN** a dynamic parent at a non-zero offset contains a `SwitchElement` (the `RouterView` pattern) and the switch's condition is toggled repeatedly
- **THEN** the DOM nodes of the preceding siblings SHALL remain present and in order after each toggle, and the switch's branch content SHALL be positioned after them

#### Scenario: Re-indexing a dynamic parent at offset 0 is unchanged
- **WHEN** a dynamic container sits at `_node_idx == 0` (e.g., `RouterView` as the sole child of its parent) and `_re_index_children` runs after a refresh or as part of `RouterView._on_set_parent`
- **THEN** the assigned child indices SHALL equal the values produced under base `0` (preserving current behavior for the common case)

### Requirement: `_re_index_children` SHALL eagerly propagate a changed base index into inline Teleports

A non-recursive `_re_index_children` pass SHALL propagate the newly assigned base index one level into each `TeleportElement` child whose `_node_idx` changed during the pass: the teleport's subtree SHALL be re-indexed immediately (`child._re_index_children(False)`) before the pass continues with the next sibling. Inline-fallback Teleports are the only dynamic elements that require this: their children are positioned in the parent's slot and must re-index against the teleport's updated position without waiting for the teleport's next render — for example, an inline-fallback `TeleportElement` wrapping a `RepeatElement` must re-index when a preceding sibling grows. Other `DynamicElement` children (RepeatElement, SwitchElement, SuspenseElement, FragmentElement, etc.) SHALL keep their lazy semantics: their subtrees are re-indexed on their own render/refresh paths, and the pass SHALL NOT descend into them. The propagation SHALL terminate: it descends only into teleport children whose `_node_idx` actually changed, and each level propagates at most once per pass, so the re-entrant pass issued by an inline `TeleportElement` (which re-indexes itself against the parent) SHALL find stable indices and stop. A recursive pass (`recursive=True`) SHALL retain its full-depth behavior.

#### Scenario: Inline Teleport subtree re-indexes after preceding sibling growth
- **WHEN** a container's non-recursive `_re_index_children` pass changes a `TeleportElement` child's base index
- **AND** the teleport is in inline-fallback mode and its subtree contains a `RepeatElement`
- **THEN** the changed base index SHALL propagate one level into the teleport in the same pass
- **AND** the inline teleport SHALL re-index its children against the parent's pass
- **AND** the repeat's children SHALL receive updated `_node_idx` values aligned with the teleport's new position, with no node drift, re-indexing errors, or unbounded recursion

#### Scenario: Non-teleport dynamic siblings keep lazy re-indexing
- **WHEN** a container's non-recursive `_re_index_children` pass changes the base index of a `RepeatElement`/`SwitchElement`/`SuspenseElement`/`FragmentElement` child that does not contain an inline Teleport
- **THEN** the pass SHALL NOT descend into that child's subtree; the child's own render/refresh path SHALL re-index the subtree

### Requirement: DynamicElement `_refresh_sync` pattern shall use a shared helper

A `_run_refresh_sync(refresh: Callable[..., Coroutine[Any, Any, Any]], *args: Any) -> None` helper SHALL be defined in `webcompy/elements/types/_dynamic.py`. The helper SHALL encapsulate the nest_asyncio + loop.run_until_complete sync-wrapping logic. `SwitchElement._refresh_sync` and `RepeatElement._refresh_sync` SHALL delegate to `_run_refresh_sync` instead of containing their own copies of the sync-wrapper logic.

#### Scenario: SwitchElement uses shared helper
- **WHEN** `SwitchElement._refresh_sync` is called
- **THEN** it SHALL delegate to `_run_refresh_sync(self._refresh, *args)`
- **AND** the runtime behavior SHALL be identical to the pre-extraction implementation

#### Scenario: RepeatElement uses shared helper
- **WHEN** `RepeatElement._refresh_sync` is called
- **THEN** it SHALL delegate to `_run_refresh_sync(self._refresh, *args)`
- **AND** the runtime behavior SHALL be identical to the pre-extraction implementation

#### Scenario: New DynamicElement subclasses use shared helper
- **WHEN** a new `DynamicElement` subclass (e.g., `MarkdownForElement`) requires `_refresh_sync` semantics
- **THEN** it SHALL use `_run_refresh_sync(self._refresh, *args)` without duplicating the sync-wrapper logic

### Requirement: Synchronous refresh dispatch shall not block the event loop in the Pyodide environment

`_run_refresh_sync` SHALL NOT call `loop.run_until_complete` when running in the Pyodide environment (`ENVIRONMENT == "pyscript"`). Instead, the refresh coroutine SHALL be scheduled on the event loop (via the existing `aio_run` mechanism) so it completes fully without raising "Cannot stack switch"; exceptions raised by the refresh SHALL be logged with a formatted traceback (via `_log_error`, the same logging path used by `_resolve_async_callback`) rather than propagated into the DOM event handler. In non-Pyodide environments, `_run_refresh_sync` SHALL keep its current synchronous behavior (`asyncio.run` without a running loop; `nest_asyncio` + `run_until_complete` with one), so a refresh SHALL complete before the call returns.

#### Scenario: Signal-driven refresh from a DOM event handler completes in Pyodide
- **WHEN** a signal-driven refresh (`RepeatElement`, `SwitchElement`, or `MarkdownForElement`) is dispatched from a synchronous DOM event handler in the Pyodide environment
- **THEN** the refresh coroutine SHALL be scheduled on the event loop and run to completion without raising "Cannot stack switch"
- **AND** a failed refresh SHALL log a formatted traceback via the logging facility instead of surfacing as an uncaught pageerror

#### Scenario: Refresh remains synchronous outside Pyodide
- **WHEN** `_run_refresh_sync` is called in a non-Pyodide environment with a running event loop
- **THEN** the refresh SHALL complete synchronously before `_run_refresh_sync` returns (existing behavior preserved)

### Requirement: Pre-rendered DOM nodes shall be reused during hydration via adopt-and-hydrate
When full hydration is enabled, elements SHALL use `_hydrate_node()` instead of `_init_node()` for prerendered nodes. `_hydrate_node()` SHALL check for an existing prerendered node and delegate to `_adopt_node()` if found, or fall back to `_init_node()` if not. This enables efficient hydration of server-rendered content. This requirement applies to all node types including `#text` nodes, and to content under dynamic containers (RouterView, Suspense, Transition, ErrorBoundary) whose children are created during the hydration pass. During hydration, attribute values and text content SHALL only be written if they differ from the prerendered values to avoid redundant DOM operations. Adoption SHALL NOT end an element's hydration: adopted elements SHALL still complete exactly one hydration render pass so reactive registrations are established (see "Adopted children of dynamic containers shall complete a hydration render").

#### Scenario: Hydrating an existing prerendered element
- **WHEN** `_hydrate_node()` is called and a prerendered node with matching tag exists
- **THEN** `_adopt_node(node)` SHALL be called to adopt the existing DOM node
- **AND** the framework SHALL NOT call `_mount_node()` since the node is already in the DOM

#### Scenario: No prerendered node available during hydration
- **WHEN** `_hydrate_node()` is called and no prerendered node exists
- **THEN** the element SHALL fall back to `_init_node()` for normal DOM creation and mounting

#### Scenario: Hydration fallback creates the node exactly once
- **WHEN** `_hydrate_node()` falls back because no matching prerendered node exists (or the existing node's tag mismatches)
- **THEN** the fallback SHALL create exactly one node for the element
- **AND** the created node SHALL be recorded as the element's node so a later `_get_node()`/render reuses it (no orphan node)
- **AND** node initialization (`_init_new_node`: attributes, event handlers, ref binding) SHALL run once on the reused node

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

#### Scenario: Prerendered route content under a dynamic container is reused
- **WHEN** the browser hydrates a page whose routed content (RouterView subtree) was prerendered by SSR/SSG
- **AND** the client-side component tree matches the prerendered structure
- **THEN** the prerendered DOM nodes of the routed content SHALL be adopted
- **AND** the number of DOM nodes removed during hydration SHALL be zero for the matching content

#### Scenario: Hydrating a raw-HTML wrapper with matching content
- **WHEN** the browser finds an existing prerendered node for a `RawHTMLElement` (wrapper tag matches)
- **AND** the node's current content (`innerHTML`, or `textContent` when `innerHTML` is unavailable) equals the element's rendered value
- **THEN** the wrapper node SHALL be adopted
- **AND** the framework SHALL NOT rewrite the content
- **AND** the wrapper's existing child nodes SHALL remain in the document (neither removed nor recreated)
- **AND** no mismatch record SHALL be created

### Requirement: Hydration SHALL normalize parser-merged text nodes to element-tree granularity before index-based adoption

`ElementWithChildren._hydrate_node()` SHALL NOT assume a pristine 1:1 correspondence between the element tree's child nodes and the browser DOM's `childNodes`. The HTML parser merges adjacent `#text` nodes during parsing, so a sequence of consecutive `TextElement` children (e.g. whitespace and interpolation holes adjacent in a composite body) can correspond to a single merged DOM `#text` node. Before per-child adoption proceeds by `_node_idx`, hydration SHALL detect a consecutive run of `TextElement` children and SHALL split the merged DOM `#text` node via `splitText(offset)` at the cumulative expected-text boundary of each child in the run, so that each element-tree child once again has a distinct DOM node at its `_node_idx`.

Normalization SHALL walk a **live DOM cursor**: runs SHALL be processed in element order at their current DOM position, re-reading `childNodes` as splits insert nodes, and SHALL NOT rely on indices or child counts computed before normalization began. This guarantees that a later run remains aligned after an earlier run was split, and that a run is never split using stale pre-normalization indices.

Normalization SHALL split at **every** boundary of a run, including zero-length boundaries, and SHALL detect an already-normalized run by checking that EVERY expected node (including empty ones) is present at its position — an empty trailing `TextElement` (`["a", ""]`, `["a", "", ""]`) SHALL receive its own `#text` node. A run whose children are all empty and whose DOM position has no `#text` node (the parser emits nothing for empty text) SHALL be materialized as one empty prerendered `#text` node per child, inserted at the run's position. `splitText` offsets SHALL be UTF-16 code-unit lengths (the browser `Text.splitText` unit), not Python code-point counts, so astral-plane characters split at the correct boundary.

Normalization SHALL be idempotent: when the DOM already has a 1:1 correspondence (no merging occurred, or splitting has already been applied), no further split SHALL be performed. Normalization SHALL apply only to the hydration path (`_hydrate_node`); server-side rendering, `_render`, refresh, reconcile, and positioning code SHALL remain unchanged.

When the merged DOM text content does not equal the concatenation of the run's expected text contents, hydration SHALL record a `text` mismatch (see the hydration-mismatch diagnostics requirement below), SHALL NOT split the run, and SHALL halt normalization for the remainder of that container so that the affected run (and everything after it) follows the existing per-node create/adopt fallback — the pre-fix behavior — rather than producing a misaligned split. When a non-`#text` node occupies a text-run position, hydration SHALL record a `tag` mismatch with the expected identity `#text` and the owning component ID when known. No exception SHALL propagate to the caller.

This requirement applies to `ElementWithChildren._hydrate_node` (regular containers indexing from base `0`) and to dynamic-container hydration paths (`DynamicElement._hydrate_node`, `RepeatElement`, `FragmentElement`) that rely on the same index-based `childNodes` adoption. A `NewLine` (`<br>`) or `RawHTML` (wrapper element) child renders a non-`#text` DOM node and SHALL terminate a text run; only consecutive `TextElement` children participate in a run.

#### Scenario: Hydrating a fragment body with merged adjacent text
- **WHEN** a keyed loop item's body is a fragment containing `<span>` + a `TextElement` + another `TextElement`, and the browser parser has merged the two `#text` nodes into one
- **THEN** `_hydrate_node` SHALL split the merged DOM `#text` node at the cumulative expected-text boundary so each `TextElement` adopts its own `#text` node at the correct `_node_idx`
- **AND** subsequent reconcile/positioning SHALL observe a 1:1 element-to-DOM correspondence

#### Scenario: No merge leaves the DOM untouched
- **WHEN** hydration encounters children whose DOM `childNodes` already correspond 1:1 to the element tree (no adjacent text was merged)
- **THEN** `_hydrate_node` SHALL perform no `splitText` calls
- **AND** adoption SHALL proceed exactly as before this change

#### Scenario: Multiple merged runs in one container are all normalized
- **WHEN** a container has two separate runs of adjacent text separated by an element (e.g. `[a, b, <span>, c, d]` with the parser merging each run), and the second run's logical position is at or beyond the container's initial `childNodes` length
- **THEN** BOTH runs SHALL be split (the live DOM cursor keeps the second run aligned after the first split)

#### Scenario: Trailing empty text children receive their own nodes
- **WHEN** a text run ends in empty `TextElement` children (`["a", ""]` or `["a", "", ""]`) and the parser merged them into the preceding text
- **THEN** each empty child SHALL adopt its own empty `#text` node at its `_node_idx`

#### Scenario: All-empty text runs with no DOM node are materialized
- **WHEN** a run consists only of empty text children (the parser emits nothing for them, so no `#text` node exists at the run's position)
- **THEN** hydration SHALL insert one empty prerendered `#text` node per child at the run's position before adoption proceeds

#### Scenario: Astral text is split at UTF-16 boundaries
- **WHEN** a run splits non-BMP text (e.g. `["😀", "x"]` merged into one node)
- **THEN** the split SHALL occur at the UTF-16 code-unit boundary so each child adopts the correct text without rewriting

#### Scenario: Content mismatch falls back rather than mis-splitting
- **WHEN** the merged DOM `#text` content does not equal the concatenation of a text run's expected contents (e.g. unexpected prerendered content)
- **THEN** hydration SHALL skip splitting that run and halt normalization for the remainder of the container (pre-fix create/adopt fallback)
- **AND** a `text` mismatch record SHALL be created for the run
- **AND** no exception SHALL propagate to the caller

#### Scenario: A non-text node at a text-run position is a structural mismatch
- **WHEN** a DOM node whose `nodeName` is not `#text` occupies a text-run position
- **THEN** hydration SHALL record a `tag` mismatch with expected identity `#text` and the actual node name
- **AND** the owning component ID SHALL be attached when known
- **AND** normalization SHALL halt for the remainder of the container

#### Scenario: Keyed ReactiveDict loop hydrates with a composite item body
- **WHEN** a `ReactiveDict` keyed loop renders items whose body contains multiple elements interleaved with text, and the prerendered HTML is parsed by the browser
- **THEN** hydration SHALL normalize the merged text nodes for every item
- **AND** a subsequent mutation that reorders keys SHALL reconcile children to the correct DOM positions without empty nodes or leftover prerendered nodes

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

### Requirement: Fresh node initialization shall not remove webcompy-managed sibling nodes

When `_init_node` finds an existing DOM node at an element's `_node_idx` that is not an adoptable prerendered node, it SHALL remove that node only if the node is not webcompy-managed (`__webcompy_node__` is not set). A webcompy-managed node found at the target index SHALL be left in place; the element SHALL create its own node and rely on `_mount_node` to insert it at the correct position via `insertBefore`. Prerendered nodes that do not match the element (tag or node-type mismatch) SHALL still be removed and recreated, since prerendered nodes never carry `__webcompy_node__`. This applies to `ElementBase._init_node`, `TextElement._init_node`, and `RawHTMLElement._init_node`, matching the existing guarded behavior of `NewLine._init_node`.

#### Scenario: Unkeyed for-loop refresh preserves following siblings
- **WHEN** a template contains `{% for item in items %}` over a `ReactiveList` followed by a static sibling element inside the same parent, and the list is mutated (e.g., item appended)
- **THEN** the refreshed DOM SHALL still contain the following sibling at its original position after the rendered items

#### Scenario: Keyed (dict) repeat insertion preserves following siblings
- **WHEN** a `{% for k, v in d %}` over a `ReactiveDict` is followed by a static sibling element and a new key is inserted
- **THEN** the refreshed DOM SHALL contain the new item's element and SHALL still contain the following sibling

#### Scenario: If-branch toggle preserves following siblings
- **WHEN** an `{% if %}` whose branches use non-patchable tags (e.g., `<span>` vs `<em>`) is followed by a static sibling element and the condition signal toggles
- **THEN** the incoming branch's element SHALL be rendered and the following sibling SHALL still be present in the DOM

#### Scenario: MarkdownFor refresh preserves following siblings
- **WHEN** a `MarkdownForElement` over an empty `ReactiveList` is followed by a static sibling element and the first item is appended to the list
- **THEN** the refreshed DOM SHALL contain the rendered `<ul>` before the sibling and SHALL still contain the following sibling at its original position

#### Scenario: Prerendered tag mismatch is still discarded
- **WHEN** hydration encounters a prerendered node at an element's index whose tag does not match the element
- **THEN** the prerendered node SHALL be removed and a fresh node SHALL be created, as before

### Requirement: DynamicElement._hydrate_node shall schedule via AsyncSchedulerPort

`DynamicElement._hydrate_node()` SHALL schedule the async render of unmounted children via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(child._render())` instead of calling `asyncio.ensure_future()` directly. The scheduled task SHALL be tracked in `self._pending_render_tasks` as before, and a done callback SHALL log exceptions via `webcompy.logging.error`. This routes all async scheduling through the central port, ensuring server-side renders guarantee task completion before context disposal.

#### Scenario: Hydrating an unmounted child via the scheduler port
- **WHEN** `DynamicElement._hydrate_node()` encounters a child that is not mounted
- **THEN** the child's `_render()` coroutine SHALL be scheduled via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(child._render())`
- **AND** the returned task SHALL be appended to `self._pending_render_tasks`
- **AND** a done callback SHALL be attached that logs exceptions and removes the task from `_pending_render_tasks`

### Requirement: SuspenseElement shall schedule browser resolution via AsyncSchedulerPort

`SuspenseElement._browser_render()` and `SuspenseElement._hydrate_node()` SHALL schedule async resolution coroutines via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(coro)` instead of calling `asyncio.ensure_future()` directly. The scheduled task SHALL be tracked in `self._pending_tasks` as before.

#### Scenario: Suspense schedules browser resolution via the scheduler port
- **WHEN** `SuspenseElement._browser_render()` determines that children have unresolved async setup
- **THEN** the resolution coroutine SHALL be scheduled via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(self._browser_resolve(...))`
- **AND** the returned task SHALL be appended to `self._pending_tasks`

#### Scenario: Suspense hydrate schedules resolution via the scheduler port
- **WHEN** `SuspenseElement._hydrate_node()` determines that children lack resolved data
- **THEN** the resolution coroutine SHALL be scheduled via `inject(ASYNC_SCHEDULER_PORT_KEY).schedule(self._browser_resolve())`
- **AND** the returned task SHALL be appended to `self._pending_tasks`

### Requirement: ElementAbstract shall expose a _children attribute for uniform tree-walking

`ElementAbstract` (the common root of `Element`, `Component`, `TextElement`, and all `DynamicElement` subclasses) SHALL declare a `_children: list[ElementAbstract]` attribute. Because framework tree-walking code (Suspense async collection, hydration resolution checks, dynamic-element reconciliation) operates on values typed as `ElementAbstract` and must recurse into child nodes, the `_children` attribute SHALL be reachable through the base type rather than only on specific subclasses. Leaf node types (e.g. `TextElement`) SHALL inherit an empty `_children` list that is never mutated. This declaration SHALL NOT change any runtime child-management behavior; it only reflects the existing runtime invariant in the static type system.

#### Scenario: Suspense collects pending async components through the base type
- **WHEN** `SuspenseElement._collect_pending_coroutines` walks an element subtree typed as `ElementAbstract`
- **THEN** it SHALL be able to read `element._children` on any node without an `isinstance` narrowing or `hasattr` bypass
- **AND** `uv run pyright` SHALL report no `reportAttributeAccessIssue` warning for the access

#### Scenario: Hydration resolution check recurses through the base type
- **WHEN** `SuspenseElement._hydrate_node` checks whether all descendants have resolved hydration data
- **THEN** the recursion SHALL read `element._children` through the `ElementAbstract` annotation
- **AND** leaf nodes (e.g. `TextElement`) SHALL expose an empty `_children` list so iteration is a no-op

#### Scenario: Leaf element inherits an empty non-mutated children list
- **WHEN** a `TextElement` instance is created
- **THEN** it SHALL inherit the class-level `_children` default of `[]`
- **AND** no framework code SHALL append to or replace a leaf element's `_children`
### Requirement: Form elements shall support `:bind` two-way binding

The `:bind` attribute SHALL provide two-way binding between a writable `Signal` and a form element. It SHALL expand into (a) a one-way attribute binding (Signal→DOM, using the existing reactive attribute pipeline) and (b) a write-back event handler (DOM→Signal) registered through the standard event lifecycle (`create_proxy` on attach, `destroy` on detach). The expansion SHALL happen at `Element` construction time, so the element API and the template path behave identically.

Supported elements and rules:

| Element | Bound attribute | Event | Write-back |
|---|---|---|---|
| `input` with `type` of `text`/`email`/`password`/`search`/`tel`/`url` or no `type` | `value` | `input` | `signal.value = ev.target.value` |
| `textarea` | text content (child `TextElement`) | `input` | `signal.value = ev.target.value` |
| `input[type=number]` | `value` | `input` | converted per the number-conversion requirement below |
| `input[type=checkbox]` | `checked` | `change` | `signal.value = bool(ev.target.checked)` |
| `input[type=radio]` | `checked` | `change` | if `ev.target.checked`, set the Signal to the element's static `value` attribute |

For `textarea`, the Signal→DOM direction binds the element's text content via a child `TextElement` (HTML textareas expose no `value` attribute); the write-back direction is unchanged.

For radio, the Signal→DOM direction SHALL use a `Computed` that compares the Signal value with the element's static `value` attribute (`checked` is true when equal), so a group of radios sharing one Signal stays in sync. The comparison SHALL be a plain Python `==` on the resolved values. In templates, HTML attribute values are always strings, so the static `value` attribute is compared as a string; a template radio bound to a non-string-valued Signal (e.g. `<input type="radio" value="1" :bind="choice">` with an int-valued Signal) SHALL NOT be rendered checked. The element API (`html.INPUT({"type": "radio", "value": 1, ":bind": choice})`) preserves non-string values and SHALL compare them without coercion. Template users SHALL bind radio groups to string-valued Signals.

The `:bind` key SHALL NOT be emitted as a DOM attribute.

#### Scenario: Text input two-way binding
- **WHEN** an element is created as `html.INPUT({":bind": text_signal})` with a `Signal("hello")`
- **THEN** the input's `value` attribute SHALL render as `"hello"`
- **AND** when the user types, the `input` event handler SHALL set `text_signal.value` to `ev.target.value`
- **AND** setting `text_signal.value = "world"` SHALL update the DOM attribute

#### Scenario: Checkbox binding
- **WHEN** `html.INPUT({"type": "checkbox", ":bind": flag_signal})` is used with a `Signal(False)`
- **THEN** the `checked` attribute SHALL reflect the Signal
- **AND** on `change`, the Signal SHALL be set to `ev.target.checked`

#### Scenario: Radio group binding
- **WHEN** two radios share one Signal: `html.INPUT({"type": "radio", "value": "a", ":bind": choice})` and `html.INPUT({"type": "radio", "value": "b", ":bind": choice})`
- **THEN** the radio whose static `value` equals `choice.value` SHALL be rendered checked
- **AND** when the second radio fires `change` with `ev.target.checked` true, `choice.value` SHALL become `"b"`
- **AND** the first radio's `checked` SHALL become false reactively

#### Scenario: Template radio value compared as string
- **WHEN** a radio is created via template `<input type="radio" value="1" :bind="choice">` with an int-valued `choice = Signal(1)`
- **THEN** the `checked` Computed SHALL compare `1 == "1"`, which is `False`
- **AND** the radio SHALL NOT be rendered checked
- **AND** template users SHALL bind radio groups to string-valued Signals; the element API (`html.INPUT({"value": 1, ":bind": choice})`) SHALL compare non-string values without coercion

#### Scenario: No :bind attribute reaches the DOM
- **WHEN** any element is created with `:bind`
- **THEN** the rendered DOM node SHALL NOT have a `:bind` attribute

#### Scenario: SSR renders bound attribute only
- **WHEN** an element with `:bind` is rendered on the server
- **THEN** the output HTML SHALL contain the bound attribute (`value` or `checked`) with the Signal's initial value
- **AND** no event registration SHALL occur server-side

### Requirement: `:bind` write-back for number inputs shall convert to the Signal's numeric type

For `input[type=number]`, the write-back handler SHALL convert `ev.target.value` to `int` when the Signal's current value is an `int` (excluding `bool`), otherwise to `float`. An empty string or an unparseable value SHALL be skipped (the Signal keeps its previous value).

#### Scenario: Integer conversion
- **WHEN** a `Signal(5)` is bound to `input[type=number]` and the user enters `"42"`
- **THEN** the Signal SHALL become `42` (int)

#### Scenario: Float conversion
- **WHEN** a `Signal(0.5)` is bound and the user enters `"1.25"`
- **THEN** the Signal SHALL become `1.25` (float)

#### Scenario: Empty input skipped
- **WHEN** a `Signal(5)` is bound and the user clears the input
- **THEN** the Signal SHALL remain `5`

### Requirement: `:bind` shall validate the Signal kind and value type at construction time

The `:bind` value SHALL be a writable `Signal` instance. `Computed`, `ReadonlySignal` (`readonly()`), `ReactiveList`, `ReactiveDict`, and non-Signal values SHALL raise `WebComPyException` naming the received type. Value-type discipline SHALL be enforced from the Signal's current value: text-like/textarea requires `str`, number requires `int`/`float` (excluding `bool`), checkbox requires `bool`. Radio requires a static `value` attribute on the element. An `input` whose `type` attribute is dynamic (`SignalBase`) combined with `:bind` SHALL raise (binding semantics cannot be determined).

#### Scenario: Computed rejected
- **WHEN** `html.INPUT({":bind": some_computed})` is used
- **THEN** `WebComPyException` SHALL be raised stating `:bind` requires a writable Signal

#### Scenario: Type mismatch rejected
- **WHEN** `html.INPUT({"type": "checkbox", ":bind": Signal("text")})` is used
- **THEN** `WebComPyException` SHALL be raised naming the required type (`bool`)

#### Scenario: Radio without static value rejected
- **WHEN** `html.INPUT({"type": "radio", ":bind": choice})` lacks a `value` attribute
- **THEN** `WebComPyException` SHALL be raised stating radio `:bind` requires a static `value` attribute

#### Scenario: Dynamic type attribute rejected
- **WHEN** `html.INPUT({"type": some_signal, ":bind": text_signal})` is used
- **THEN** `WebComPyException` SHALL be raised stating `:bind` requires a static `type` attribute

### Requirement: `:bind` shall reject unsupported elements and conflicting attributes

`:bind` on elements other than the supported set (including `select` and `option`) SHALL raise `WebComPyException` naming the supported elements. An explicit attribute duplicating the bound one (`value` for text-like/number, `checked` for checkbox/radio) SHALL raise `WebComPyException`. For `textarea`, the bound target is the text content; a non-empty children list combined with `:bind` SHALL raise `WebComPyException`. An explicit user handler for the binding event SHALL be chained: the binding write-back SHALL run first, then the user handler. An explicit static `value` attribute on a radio is REQUIRED and is NOT a conflict.

#### Scenario: select rejected
- **WHEN** `html.SELECT({":bind": sig})` is used
- **THEN** `WebComPyException` SHALL be raised naming the supported elements

#### Scenario: Conflicting value attribute rejected
- **WHEN** `html.INPUT({"value": "x", ":bind": text_signal})` is used
- **THEN** `WebComPyException` SHALL be raised stating the conflict with the explicit `value` attribute

#### Scenario: Conflicting textarea text content rejected
- **WHEN** `html.TEXTAREA({":bind": text_signal}, "default")` is used with explicit text content
- **THEN** `WebComPyException` SHALL be raised stating the conflict with explicit text content

#### Scenario: User handler chained after binding
- **WHEN** `html.INPUT({":bind": text_signal, "@input": user_handler})` is used and the user types
- **THEN** the Signal SHALL be updated first
- **AND** `user_handler` SHALL be called after the update

### Requirement: `:bind` shall accept Field objects

In addition to a writable `Signal`, the `:bind` attribute SHALL accept a `webcompy.forms.Field` instance. The binding SHALL use `field.value` as the bound signal with all per-element rules and conversions unchanged, SHALL set `field.dirty` to `True` on each write-back (before the value update), and SHALL register a `blur` handler setting `field.touched` to `True` (chained before any user `blur` handler). Type-discipline validation SHALL apply to `field.value` exactly as it does to a directly-passed `Signal`.

#### Scenario: Field accepted on text input
- **WHEN** `html.INPUT({":bind": field})` is used with a `Field` wrapping `Signal("")`
- **THEN** the input SHALL two-way-bind `field.value` exactly as if the Signal were passed directly

#### Scenario: Interaction state wiring
- **WHEN** a user types in a `:bind`-bound Field input and then blurs
- **THEN** `field.dirty.value` SHALL be `True` after the first keystroke
- **AND** `field.touched.value` SHALL be `True` after the blur

#### Scenario: Field type discipline
- **WHEN** `html.INPUT({"type": "checkbox", ":bind": field})` is used with a `Field` wrapping a non-`bool` Signal
- **THEN** `WebComPyException` SHALL be raised naming the required type

### Requirement: Event-handler invocation shall be wrapped for error routing

The framework's event-handler wrapper (`_generate_event_handler`) SHALL catch exceptions from both sync handlers and async handlers (via the `resolve_async` error path). Caught errors SHALL enter the error-handling propagation walk starting at the element the handler is attached to: `catch_events=True` boundaries engage; otherwise the error reaches `AppConfig.on_error` or is logged. Handler wrapping SHALL NOT change the existing `create_proxy`/`destroy` lifecycle — proxies are still created once and destroyed on removal.

#### Scenario: Sync handler error is routed
- **WHEN** a sync `on_click` handler raises
- **THEN** the exception SHALL NOT escape into the PyScript proxy uncaught
- **AND** it SHALL be delivered to the propagation walk (global handler or `catch_events` boundary)

#### Scenario: Async handler error is routed
- **WHEN** an async event handler's coroutine raises
- **THEN** the error SHALL be routed identically to sync handler errors (not merely logged by `resolve_async`'s default)

#### Scenario: Proxy lifecycle unchanged
- **WHEN** an element with event handlers is removed
- **THEN** its proxies SHALL still be destroyed exactly as today (no leak introduced by wrapping)

### Requirement: Adopted children of dynamic containers shall complete a hydration render

Every child of a hydrated dynamic container (`DynamicElement` subclasses: RouterView, ErrorBoundary, Switch, Repeat, Suspense, Transition, ClientOnly) SHALL complete exactly one hydration render, even when its DOM node was adopted during `_hydrate_node()` (which marks it mounted). During hydration, the parent SHALL schedule the child's render through the `ASYNC_SCHEDULER_PORT_KEY`, and the hydration render SHALL NOT skip children because they are mounted. The render's mount operations SHALL be no-ops on adopted nodes, and all DOM writes SHALL remain diff-only, so the hydration render is visually neutral when server and client content match. Outside the initial hydration, the existing render-skip semantics for mounted children SHALL be preserved.

#### Scenario: Hydration render is visually neutral for matching content
- **WHEN** a dynamic container's adopted children complete their hydration render after SSR with matching content
- **THEN** no DOM node REMOVAL or insertion SHALL occur as a result of the hydration render
- **AND** the element's reactive registrations (signal callbacks, key maps, rendered-branch state) SHALL be established

#### Scenario: Reactive behavior works after adopting a hydrated switch
- **WHEN** a `Switch` branch was adopted from prerendered DOM inside a hydrated dynamic container
- **AND** a user interaction flips the switch condition after hydration completes
- **THEN** the DOM SHALL update to the new branch
- **AND** the adopted branch's DOM nodes SHALL be reused when the branch structure matches (patching), preserving node identity

#### Scenario: Adopted switch branch containing a dynamic element stays wired
- **WHEN** the adopted branch of a hydrated `Switch` contains a dynamic element (e.g., a `Repeat` over a transferred list)
- **THEN** the branch subtree SHALL complete exactly one hydration render (the scheduled hydration-render wrappers SHALL NOT be cancelled by the unchanged-branch first refresh)
- **AND** the nested dynamic element's reactive wiring SHALL be established (e.g., list mutations update the DOM after hydration)

#### Scenario: Refresh outside hydration keeps mounted-skip behavior
- **WHEN** a dynamic container refreshes after hydration (signal-triggered refresh)
- **THEN** mounted children SHALL NOT be re-rendered merely because they are mounted (existing refresh semantics SHALL be preserved)

### Requirement: Repeat shall preserve adopted SSR children on the first hydration refresh

When a `Repeat` element's children were adopted from prerendered DOM during hydration, the first refresh SHALL NOT remove and re-create them (the pre-change full-rebuild path). Instead, the first refresh SHALL treat adopted children as already-materialized items: it SHALL reposition them to match the current sequence, SHALL rebuild the key map (`_populate_key_map()` equivalent), and SHALL render only children that have no adopted node. Subsequent refreshes SHALL follow the existing keyed-reconciliation semantics.

#### Scenario: Repeat over transferred list value preserves SSR nodes after hydration
- **WHEN** a `Repeat` renders a `ReactiveList` whose value was transferred from SSR
- **AND** the repeat's children were adopted from the prerendered DOM during hydration
- **AND** the hydration render triggers the repeat's first refresh
- **THEN** the adopted DOM nodes SHALL remain in the document (no removal)
- **AND** the key map SHALL be populated from the current sequence

#### Scenario: Repeat list mutation after hydration reconciles correctly
- **WHEN** a `Repeat` with a transferred list value receives a mutation after hydration (e.g., `pop`, `append`)
- **THEN** the DOM SHALL reconcile to the new sequence
- **AND** key-based reuse SHALL apply for keyed repeats as before

#### Scenario: Repeat with partial SSR coverage preserves matched nodes
- **WHEN** a `Repeat`'s SSR DOM covers only a subset of the sequence (fewer nodes than items, or a per-item tag mismatch at one position)
- **AND** the first hydration refresh runs
- **THEN** the adopted (matched) DOM nodes SHALL remain in the document
- **AND** the missing positions SHALL be created and rendered (via the scheduled plain-render tasks), matching the current sequence

### Requirement: Switch shall inherit the rendered branch from SSR content during hydration

When a `Switch` element's active branch was prerendered by SSR, hydration SHALL initialize the switch's rendered-branch state so that the first refresh with an unchanged condition SHALL NOT regenerate the branch. The adopted branch's DOM nodes SHALL be reused. If the condition already changed relative to SSR (e.g., restored state differs), the switch SHALL patch to the new branch via the existing `_patch_children` flow.

#### Scenario: First refresh with unchanged condition does not regenerate
- **WHEN** a hydrated `Switch` receives a refresh triggered by an unrelated signal (or its own render runs)
- **AND** the active branch condition matches the SSR-rendered branch
- **THEN** the branch SHALL NOT be removed and re-generated
- **AND** the adopted DOM nodes SHALL remain in the document

#### Scenario: Condition changed after hydration patches to the new branch
- **WHEN** the switch condition changes after hydration so a different branch becomes active
- **THEN** the DOM SHALL switch to the new branch via patching (existing behavior)
- **AND** matching single-node branches SHALL reuse their adopted nodes

### Requirement: Hydration mismatches shall be recorded with recovery or repair

During hydration, five classes of divergence between the prerendered DOM and the client element tree SHALL be detected and recorded: text mismatch and attribute mismatch (recoverable — the mismatch SHALL be patched by writing the expected value into the adopted node), raw-HTML mismatch (recoverable — when an adopted raw-HTML wrapper's existing content differs from the element's rendered value, the mismatch SHALL be patched by re-applying the rendered value into the adopted node), and tag mismatch and node-count mismatch (structural — the mismatch SHALL be repaired by removing the stale node and creating the expected one). Each record SHALL capture the mismatch class, the expected value, the actual value, and the owning component ID when known. Records SHALL be collected for aggregation and reporting by the app layer (see the async-rendering capability). Records SHALL NOT be emitted as individual console messages.

Leaf element types (`TextElement`, `RawHTMLElement`, `NewLine`) SHALL resolve the owning component ID through their parent chain (`self._parent._get_belonging_component()`), guarded against a missing or broken parent chain (an unresolved chain SHALL yield an empty ID rather than raising), so text, raw-HTML, and tag records attributed to a component are attributable in the aggregated report.

#### Scenario: Recoverable text mismatch is patched and recorded
- **WHEN** hydration adopts a prerendered `#text` node whose content differs from the client element's expected text
- **THEN** the node content SHALL be updated to the expected text
- **AND** a text-mismatch record SHALL be created
- **AND** no DOM node SHALL be removed

#### Scenario: Structural tag mismatch is repaired and recorded
- **WHEN** hydration finds a prerendered node whose tag differs from the client element's tag at the same position
- **THEN** the stale node SHALL be removed and the expected node SHALL be created (repair)
- **AND** a tag-mismatch record SHALL be created

#### Scenario: Recoverable raw-HTML mismatch is patched and recorded
- **WHEN** hydration adopts a prerendered raw-HTML wrapper whose existing content differs from the element's rendered value
- **THEN** the wrapper's content SHALL be updated to the rendered value
- **AND** a raw_html-mismatch record SHALL be created
- **AND** the wrapper node itself SHALL be preserved (not removed or recreated)

#### Scenario: Leaf text and raw-HTML records carry the owning component ID
- **WHEN** a `TextElement`, `RawHTMLElement`, or `NewLine` produces a text, raw_html, or tag mismatch record during hydration
- **THEN** the record's component ID SHALL equal the owning component ID resolved through the parent chain
- **AND** the component ID SHALL be empty (rather than raising) when no parent chain resolves it

#### Scenario: Matching content produces no records
- **WHEN** hydration adopts prerendered content that fully matches the client element tree
- **THEN** no mismatch records SHALL be created

#### Scenario: Excess prerendered children yield a single node-count record
- **WHEN** a container's prerendered node has N excess child nodes beyond the element tree's child count
- **THEN** a SINGLE `node-count` record SHALL be created capturing the element tree's child count as the expected value and the pre-cleanup child node count as the actual value
- **AND** all N excess nodes SHALL be removed

### Requirement: Hydration shall consume Teleport SSR blocks exactly once

During hydration, a Teleport whose children were emitted server-side SHALL locate its block under the resolved target using the marker contract, claim it exclusively against the per-context registry (a claimed ordinal SHALL NOT be consumable by another Teleport instance), remove the claimed start/end markers and their enclosed nodes, and then render its children through the normal client mount path at the reclaimed slot so that each piece of teleported content appears exactly once in the final document. A Teleport that finds no matching unclaimed block SHALL proceed via its existing self-scheduled client render and SHALL schedule a warning. If a hydrated Teleport is destroyed before consuming its block (for example an error boundary replacing an ancestor), any unconsumed block it had claimed or could uniquely identify SHALL be swept to prevent orphaned duplicates; a teleport destroyed without identification leaves the inert SSR content in place as ordinary served markup. Block consumption SHALL preserve sibling index accounting: removing a claimed block updates indices of following siblings of the target, including other teleports' blocks, before they are consumed.

#### Scenario: Server-emitted dropdown is consumed without duplication

- **WHEN** a page hydrates whose SSR HTML contains one `wc-teleport-block` under `<body>` for a navbar dropdown
- **THEN** after hydration the dropdown's DOM nodes exist exactly once, managed by the client-side Teleport
- **AND** neither the marker comments nor the original server-emitted copies remain under `<body>`

#### Scenario: Stale HTML falls back to self-mount

- **WHEN** hydration runs against HTML with no teleport blocks (e.g. generated by a pre-emission build)
- **THEN** each Teleport logs a warning and mounts its children via the existing self-render path
- **AND** the page ends with exactly one live copy of each teleported subtree

#### Scenario: Claimed ordinal is not double-consumed

- **WHEN** two Teleports share target `body` and both have emitted blocks with ordinals 0 and 1
- **THEN** the first hydrating Teleport claims ordinal 0's block and the second claims ordinal 1's
- **AND** no block is consumed twice and no live content is duplicated

#### Scenario: Destruction during hydration sweeps unconsumed blocks

- **WHEN** an error boundary above a hydrated-but-unconsumed Teleport replaces the subtree, and the unclaimed block is identifiable
- **THEN** the identified server-emitted block is removed from the target
- **AND** no orphaned duplicate of teleported content remains under the target
